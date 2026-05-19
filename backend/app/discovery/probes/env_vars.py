"""Probe well-known env vars that already hold a base URL."""

from __future__ import annotations

import os

from ._http import get
from .fingerprint import classify
from ..types import FoundEndpoint, FoundObservability, FoundVectorStore

KNOWN_VARS: list[tuple[str, str]] = [
    ("OPENAI_API_BASE", "/v1/models"),
    ("OPENAI_BASE_URL", "/v1/models"),
    ("AZURE_OPENAI_ENDPOINT", "/openai/deployments"),
    ("ANTHROPIC_BASE_URL", "/v1/models"),
    ("OLLAMA_HOST", "/api/tags"),
    ("OLLAMA_BASE_URL", "/api/tags"),
    ("VLLM_BASE_URL", "/v1/models"),
    ("MLFLOW_TRACKING_URI", "/api/2.0/mlflow/experiments/list"),
    ("LANGFUSE_HOST", "/api/public/health"),
    ("QDRANT_URL", "/collections"),
    ("WEAVIATE_URL", "/v1/.well-known/ready"),
]


def run(environ: dict[str, str] | None = None) -> tuple[
    list[FoundEndpoint], list[FoundVectorStore], list[FoundObservability]
]:
    env = environ if environ is not None else dict(os.environ)
    endpoints: list[FoundEndpoint] = []
    vectors: list[FoundVectorStore] = []
    observ: list[FoundObservability] = []

    for var, path in KNOWN_VARS:
        raw = env.get(var)
        if not raw:
            continue
        base = raw.rstrip("/")
        if not base.startswith(("http://", "https://")):
            base = "http://" + base
        probed = get(base + path)
        if not probed.ok and probed.status not in (401, 403):
            continue
        e, v, o = classify(probed)
        if e:
            e.source = f"env:{var}"
            e.provider_label = var
            endpoints.append(e)
        if v:
            v.source = f"env:{var}"
            vectors.append(v)
        if o:
            o.source = f"env:{var}"
            observ.append(o)
    return endpoints, vectors, observ
