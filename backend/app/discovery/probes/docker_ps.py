"""Read `docker ps` and surface containers that look like LLM services.

This probe never starts containers, never inspects images by hash, never
pulls anything. It calls `docker ps --format json` once, parses the output,
and emits one record per matching container.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Iterable

from ._http import get
from .fingerprint import classify
from ..types import FoundContainer, FoundEndpoint, FoundObservability, FoundVectorStore


IMAGE_HINTS: dict[str, str] = {
    # framework hint → image substring
    "ollama": "ollama",
    "vllm": "vllm",
    "tgi": "text-generation-inference",
    "triton": "tritonserver",
    "llama_cpp": "llama.cpp",
    "qdrant": "qdrant",
    "weaviate": "weaviate",
    "milvus": "milvusdb",
    "mlflow": "mlflow",
    "langfuse": "langfuse",
    "phoenix": "arize-phoenix",
}

# Common containers that *look* AI-shaped by name but aren't endpoints
# (postgres / redis under a langfuse stack, for example).
SKIP_IMAGE: tuple[str, ...] = ("postgres", "redis", "minio", "rabbitmq")


_PORT_RE = re.compile(r"0\.0\.0\.0:(\d+)->(\d+)/tcp")


def _hint_from_image(image: str) -> str | None:
    img = image.lower()
    if any(s in img for s in SKIP_IMAGE):
        return None
    for hint, needle in IMAGE_HINTS.items():
        if needle in img:
            return hint
    return None


def _published_ports(ports_field: str) -> list[int]:
    return [int(m.group(1)) for m in _PORT_RE.finditer(ports_field or "")]


def run() -> tuple[
    list[FoundContainer],
    list[FoundEndpoint],
    list[FoundVectorStore],
    list[FoundObservability],
]:
    try:
        proc = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return [], [], [], []
    if proc.returncode != 0:
        return [], [], [], []

    containers: list[FoundContainer] = []
    endpoints: list[FoundEndpoint] = []
    vectors: list[FoundVectorStore] = []
    observ: list[FoundObservability] = []

    for line in proc.stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        image = row.get("Image", "")
        hint = _hint_from_image(image)
        if hint is None:
            continue
        ports = _published_ports(row.get("Ports", ""))
        containers.append(
            FoundContainer(
                name=row.get("Names", "").split(",")[0],
                image=image,
                ports=ports,
                framework=hint,
            )
        )
        # For every published port, attempt a fingerprint. We try a
        # sensible health path per framework — same logic as the local
        # ports probe but the framework is already known.
        for port in ports:
            health = _health_path_for(hint)
            probed = get(f"http://127.0.0.1:{port}{health}")
            if not probed.ok and probed.status not in (401, 403):
                continue
            e, v, o = classify(probed)
            for rec in (e, v, o):
                if rec is not None:
                    rec.source = f"docker:{row.get('Names','').split(',')[0]}"
            if e:
                e.provider_label = image
                endpoints.append(e)
            if v:
                vectors.append(v)
            if o:
                observ.append(o)

    return containers, endpoints, vectors, observ


def _health_path_for(framework: str) -> str:
    return {
        "ollama": "/api/tags",
        "vllm": "/v1/models",
        "tgi": "/info",
        "qdrant": "/collections",
        "weaviate": "/v1/.well-known/ready",
        "milvus": "/healthz",
        "mlflow": "/api/2.0/mlflow/experiments/list",
        "langfuse": "/api/public/health",
        "phoenix": "/health",
    }.get(framework, "/")
