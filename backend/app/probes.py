"""Probe subsystem.

Probes are **scoped to endpoints declared in the loaded config**. This
service is an internal-observability sidecar, not a discovery scanner —
it will not reach for hosts you did not tell it about.

Default probe payload assumes an OpenAI-compatible API:
    GET  <baseUrl>/v1/models             — model listing
    POST <baseUrl>/v1/chat/completions   — chat sanity-ping (optional)

Override per-endpoint by setting `healthPath` in the config.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .models import Endpoint, Operation


@dataclass
class ProbeResult:
    endpoint_id: str
    reachable: bool
    status_code: int | None
    latency_ms: float | None
    inferred_operations: list[Operation]
    inferred_provider: str | None
    error: str | None
    raw_excerpt: str | None  # first ~500 chars of response, for debugging


# Map known response body hints → provider strings. Cheap, intentional —
# anything fancier belongs in aimap, not here.
_PROVIDER_HINTS: tuple[tuple[str, str], ...] = (
    ("openai", "openai"),
    ("anthropic", "anthropic"),
    ("vllm", "vllm"),
    ("text-generation-inference", "tgi"),
    ("triton", "triton"),
    ("ollama", "ollama"),
    ("llama.cpp", "llama_cpp"),
)


def _auth_header(endpoint: Endpoint) -> dict[str, str]:
    """Headers for auth types we know the *shape* of, even when we don't
    have the secret. The point is to send a plausible request; a 401 is
    still a useful result (endpoint is up, auth is enforced)."""
    # Real secrets are injected via env var ATLAS_PROBE_TOKEN_<endpoint id>
    # at deployment time — we do not store credentials in the config file.
    import os
    token = os.environ.get(f"ATLAS_PROBE_TOKEN_{endpoint.id.upper()}")
    if not token:
        return {}
    if endpoint.auth_type == "bearer":
        return {"Authorization": f"Bearer {token}"}
    if endpoint.auth_type == "api_key":
        return {"x-api-key": token}
    return {}


def _infer_operations(body: str) -> list[Operation]:
    """Cheap content-shape inference from /v1/models-style responses."""
    inferred: list[Operation] = []
    lower = body.lower()
    if "chat" in lower or "messages" in lower:
        inferred.append(Operation.chat_completion)
    if "embedding" in lower:
        inferred.append(Operation.embeddings)
    if "completion" in lower and Operation.chat_completion not in inferred:
        inferred.append(Operation.completion)
    if "rerank" in lower:
        inferred.append(Operation.rerank)
    return inferred


def _infer_provider(body: str) -> str | None:
    lower = body.lower()
    for needle, label in _PROVIDER_HINTS:
        if needle in lower:
            return label
    return None


async def probe_endpoint(
    endpoint: Endpoint,
    *,
    timeout: float = 5.0,
    client: httpx.AsyncClient | None = None,
) -> ProbeResult:
    """Run a single, polite GET against an endpoint's health path."""
    url = endpoint.url.rstrip("/") + endpoint.health_path
    headers = {"User-Agent": "nuclide-atlas/0.1 (+internal)"} | _auth_header(endpoint)

    owned = client is None
    if owned:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    started = time.perf_counter()
    try:
        resp = await client.get(url, headers=headers)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        body = resp.text[:2000]
        return ProbeResult(
            endpoint_id=endpoint.id,
            reachable=True,
            status_code=resp.status_code,
            latency_ms=round(elapsed_ms, 2),
            inferred_operations=_infer_operations(body),
            inferred_provider=_infer_provider(body),
            error=None,
            raw_excerpt=body[:500],
        )
    except httpx.HTTPError as exc:
        return ProbeResult(
            endpoint_id=endpoint.id,
            reachable=False,
            status_code=None,
            latency_ms=None,
            inferred_operations=[],
            inferred_provider=None,
            error=type(exc).__name__ + ": " + str(exc),
            raw_excerpt=None,
        )
    finally:
        if owned:
            await client.aclose()


async def probe_all(endpoints: list[Endpoint], *, timeout: float = 5.0) -> dict[str, dict[str, Any]]:
    """Run probes against every configured endpoint in parallel."""
    import asyncio
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(probe_endpoint(ep, timeout=timeout, client=client) for ep in endpoints)
        )
    return {r.endpoint_id: r.__dict__ for r in results}
