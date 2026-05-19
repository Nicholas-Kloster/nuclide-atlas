"""Optional aimap delegation.

If `aimap` is on PATH we prefer it for URL probing: it carries deep
enumerators for ~36 services that this module does not. We hand it
hosts as CIDR-of-one and parse its JSON output.

When aimap is absent, Atlas falls back to `fingerprint.classify()` and
keeps moving. No hard dependency.

aimap JSON schema (v1.x): list of host records with `services[]` per host;
each service has `port`, `service`, `version`, `banner`, and sometimes
`details` (deep-enum payload). We map service → framework, and emit one
FoundEndpoint per LLM-shaped service.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from urllib.parse import urlparse

from ..types import FoundEndpoint


def available() -> bool:
    return shutil.which("aimap") is not None


_SERVICE_TO_FRAMEWORK: dict[str, str] = {
    "ollama": "ollama",
    "vllm": "vllm",
    "tgi": "tgi",
    "text-generation-inference": "tgi",
    "triton": "triton",
    "openai-compat": "openai_compat",
    "llama.cpp": "llama_cpp",
    "qdrant": "qdrant",
    "weaviate": "weaviate",
    "milvus": "milvus",
    "mlflow": "mlflow",
    "langfuse": "langfuse",
    "phoenix": "phoenix",
}


def probe_url(url: str, *, timeout: int = 15) -> list[FoundEndpoint]:
    if not available():
        return []
    host = urlparse(url).hostname or url
    try:
        proc = subprocess.run(
            ["aimap", "-target", host, "-json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    out: list[FoundEndpoint] = []
    hosts = data if isinstance(data, list) else [data]
    for record in hosts:
        services = record.get("services", []) if isinstance(record, dict) else []
        for svc in services:
            framework = _SERVICE_TO_FRAMEWORK.get(svc.get("service", "").lower())
            if framework is None:
                continue
            port = svc.get("port")
            scheme = "https" if svc.get("tls") else "http"
            base = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
            out.append(
                FoundEndpoint(
                    url=base,
                    framework=framework,
                    operations=_ops_for(framework),
                    source="aimap",
                    auth_required=bool(svc.get("auth_required")),
                )
            )
    return out


def _ops_for(framework: str) -> list[str]:
    if framework == "ollama":
        return ["chatCompletion", "completion", "embeddings"]
    if framework in {"openai_compat", "vllm"}:
        return ["chatCompletion", "completion"]
    if framework == "tgi":
        return ["completion"]
    return []
