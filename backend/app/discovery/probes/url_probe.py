"""Probe a single user-supplied URL.

This is the path behind `POST /api/import-url` and behind the UI's
"+ Add source" → "URL" button. If aimap is on PATH, we hand the host to
aimap for a richer fingerprint; otherwise we walk the standard health
paths.
"""

from __future__ import annotations

from urllib.parse import urlparse

from . import aimap_shim
from ._http import get
from .fingerprint import classify
from ..types import FoundEndpoint, FoundObservability, FoundVectorStore


PATHS_TO_TRY: list[str] = [
    "/v1/models",
    "/api/tags",
    "/info",
    "/v1/.well-known/ready",
    "/collections",
    "/api/2.0/mlflow/experiments/list",
    "/api/public/health",
    "/health",
]


def run(url: str) -> tuple[
    list[FoundEndpoint], list[FoundVectorStore], list[FoundObservability]
]:
    aimap_hits = aimap_shim.probe_url(url)
    if aimap_hits:
        return aimap_hits, [], []

    parsed = urlparse(url if "://" in url else "http://" + url)
    base = f"{parsed.scheme or 'http'}://{parsed.netloc or parsed.path}".rstrip("/")
    endpoints: list[FoundEndpoint] = []
    vectors: list[FoundVectorStore] = []
    observ: list[FoundObservability] = []
    seen_frameworks: set[str] = set()

    for path in PATHS_TO_TRY:
        probed = get(base + path)
        if not probed.ok and probed.status not in (401, 403):
            continue
        e, v, o = classify(probed)
        for rec in (e, v, o):
            if rec is not None:
                rec.source = f"url:{base}"
        if e and e.framework not in seen_frameworks:
            endpoints.append(e)
            seen_frameworks.add(e.framework or "")
        if v and v.db_type not in seen_frameworks:
            vectors.append(v)
            seen_frameworks.add(v.db_type)
        if o and o.kind not in seen_frameworks:
            observ.append(o)
            seen_frameworks.add(o.kind)

    return endpoints, vectors, observ
