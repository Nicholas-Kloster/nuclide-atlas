"""Service fingerprinting on top of a single HTTP response.

This is intentionally narrower than `aimap`: aimap covers 36 services
with deep enumerators. Atlas only needs to identify the half-dozen
shapes that produce useful graph nodes. If aimap is on PATH the bootstrap
will prefer it; this module is the fallback so a fresh clone still
works.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

from ._http import Probed, get, tcp_open
from ..types import (
    FoundEndpoint,
    FoundObservability,
    FoundVectorStore,
)


# Ports we *try first* on localhost. Each entry is (port, framework hint,
# health path). Order matters for output stability; the parser does the
# heavy lifting.
PORT_CATALOG: list[tuple[int, str, str]] = [
    (11434, "ollama", "/api/tags"),
    (8000, "openai_compat", "/v1/models"),
    (8080, "openai_compat", "/v1/models"),
    (8888, "openai_compat", "/v1/models"),
    (8081, "tgi", "/info"),
    (6333, "qdrant", "/collections"),
    (19530, "milvus", "/healthz"),
    (5000, "mlflow", "/api/2.0/mlflow/experiments/list"),
    (3100, "langfuse", "/api/public/health"),
    (6006, "phoenix", "/health"),
    (7860, "gradio", "/info"),
    (8089, "weaviate", "/v1/.well-known/ready"),
]


def fingerprint(p: Probed) -> str | None:
    """Best-effort framework label from a single response body + URL."""
    body = (p.body or "").lower()
    if "ollama" in body or "/api/tags" in p.url:
        return "ollama"
    if "vllm" in body:
        return "vllm"
    if "text-generation-inference" in body or p.url.endswith("/info"):
        return "tgi"
    if "llama.cpp" in body:
        return "llama_cpp"
    # OpenAI envelope: {"object":"list","data":[{"id":...,"object":"model"}]}
    if p.json and isinstance(p.json, dict) and p.json.get("object") == "list":
        if any(
            isinstance(it, dict) and it.get("object") == "model"
            for it in p.json.get("data", [])
        ):
            return "openai_compat"
    if "qdrant" in body:
        return "qdrant"
    if "weaviate" in body:
        return "weaviate"
    if "mlflow" in body:
        return "mlflow"
    if "langfuse" in body:
        return "langfuse"
    if "phoenix" in body or "openinference" in body:
        return "phoenix"
    if "gradio" in body:
        return "gradio"
    if "triton" in body:
        return "triton"
    return None


def extract_models(p: Probed, framework: str | None) -> list[str]:
    if not p.json:
        return []
    if framework == "ollama":
        return [m.get("name", "") for m in p.json.get("models", []) if isinstance(m, dict)]
    if framework in {"openai_compat", "vllm", "tgi"}:
        return [
            it.get("id", "") for it in p.json.get("data", []) if isinstance(it, dict)
        ]
    return []


def is_vector_store(framework: str | None) -> bool:
    return framework in {"qdrant", "weaviate", "milvus", "pinecone", "chroma"}


def is_observability(framework: str | None) -> bool:
    return framework in {"mlflow", "langfuse", "phoenix"}


def classify(probed: Probed) -> tuple[FoundEndpoint | None, FoundVectorStore | None, FoundObservability | None]:
    """Sort one probed response into endpoint / vector-store / observability."""
    fp = fingerprint(probed)
    if fp is None:
        return None, None, None
    base_url = probed.url.rsplit("/", 1)[0].rsplit("/api", 1)[0]
    # Trim known suffixes back to the base, best-effort.
    for suffix in ("/v1/models", "/api/tags", "/v1", "/info", "/collections",
                   "/api/public/health", "/api/2.0/mlflow/experiments/list"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break

    if is_vector_store(fp):
        collections: list[str] = []
        if isinstance(probed.json, dict):
            result = probed.json.get("result") or probed.json
            cols = result.get("collections") if isinstance(result, dict) else None
            if isinstance(cols, list):
                collections = [
                    c.get("name", c) if isinstance(c, dict) else str(c) for c in cols
                ]
        return None, FoundVectorStore(url=base_url, db_type=fp, collections=collections), None

    if is_observability(fp):
        return None, None, FoundObservability(url=base_url, kind=fp)

    return (
        FoundEndpoint(
            url=base_url,
            framework=fp,
            operations=_ops_for(fp),
            raw_models=extract_models(probed, fp),
            auth_required=(probed.status in (401, 403)),
        ),
        None,
        None,
    )


def _ops_for(framework: str) -> list[str]:
    if framework == "ollama":
        return ["chatCompletion", "completion", "embeddings"]
    if framework in {"openai_compat", "vllm"}:
        return ["chatCompletion", "completion"]
    if framework == "tgi":
        return ["completion"]
    return []


def probe_host_ports(
    host: str,
    ports: Sequence[tuple[int, str, str]] = PORT_CATALOG,
    *,
    workers: int = 8,
) -> list[Probed]:
    """Concurrent TCP+HTTP sweep of one host across the catalog."""
    open_ports = [(p, fw, path) for p, fw, path in ports if tcp_open(host, p)]
    results: list[Probed] = []
    if not open_ports:
        return results
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(
            lambda triple: get(f"http://{host}:{triple[0]}{triple[2]}"),
            open_ports,
        ):
            results.append(r)
    return results
