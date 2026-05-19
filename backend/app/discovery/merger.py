"""Merge probe output into the canonical Graph YAML.

Strategy:

 1. Dedupe FoundEndpoints by url+framework.
 2. Manufacture one Model per (framework, raw model id) tuple.
 3. Manufacture one Deployment per Endpoint (one container = one
    deployment, no over-thinking). The deployment's `modelId` resolves
    to the first model for that endpoint.
 4. Lift FoundVectorStores into VectorIndexes.
 5. Lift FoundObservability into Tools. (MLflow / Langfuse / Phoenix
    aren't tools in the strict sense, but rendering them under "Tools"
    keeps the column structure consistent and gives the user a single
    place to see the AI-ops layer.)
 6. Write to YAML via a tiny hand-rolled serializer so the bootstrap
    script doesn't pull pyyaml.

The output is then loaded by `config_loader.load_graph`, which validates
against the strict Pydantic schema. If something we emitted doesn't pass
validation, the bootstrap fails loud: that's the desired behavior.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from .types import (
    FoundContainer,
    FoundEndpoint,
    FoundObservability,
    FoundVectorStore,
)


# ── canonical shapes (plain dicts, no Pydantic) ─────────────────────────

@dataclass
class _AssembledGraph:
    models: list[dict] = field(default_factory=list)
    deployments: list[dict] = field(default_factory=list)
    endpoints: list[dict] = field(default_factory=list)
    rag_pipelines: list[dict] = field(default_factory=list)
    vector_indexes: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    agents: list[dict] = field(default_factory=list)
    safety_policies: list[dict] = field(default_factory=list)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str, *, fallback: str = "x") -> str:
    out = _SLUG_RE.sub("-", s.lower()).strip("-")
    return out or fallback


def merge(
    *,
    endpoints: list[FoundEndpoint],
    vectors: list[FoundVectorStore],
    observability: list[FoundObservability],
    containers: list[FoundContainer],
    timestamp: dt.datetime | None = None,
) -> _AssembledGraph:
    g = _AssembledGraph()
    timestamp = timestamp or dt.datetime.now(dt.timezone.utc)

    # endpoints / deployments / models
    seen_endpoint: set[str] = set()
    for ep in endpoints:
        key = f"{ep.url}|{ep.framework}"
        if key in seen_endpoint:
            continue
        seen_endpoint.add(key)

        framework = ep.framework or "custom"
        host_slug = _slug(ep.url.replace("http://", "").replace("https://", ""))

        # one model per raw_models entry, or a placeholder
        model_ids: list[str] = []
        raw = ep.raw_models or [f"{framework}-default"]
        for raw_name in raw:
            mid = f"m-{_slug(raw_name)}-{framework}"
            if not any(m["id"] == mid for m in g.models):
                g.models.append(
                    {
                        "id": mid,
                        "name": raw_name,
                        "providerType": _provider_for(framework),
                        "architecture": {},
                        "training": {"tags": [framework]},
                    }
                )
            model_ids.append(mid)

        # one deployment per (host, framework)
        dep_id = f"d-{host_slug}-{framework}"
        if not any(d["id"] == dep_id for d in g.deployments):
            g.deployments.append(
                {
                    "id": dep_id,
                    "modelId": model_ids[0],
                    "environment": "dev",
                    "inferenceFramework": _framework_norm(framework),
                    "resources": {"numReplicas": 1, "gpusPerReplica": 0},
                    "configuration": {},
                }
            )

        eid = f"e-{host_slug}-{framework}"
        scheme = "https" if ep.url.startswith("https://") else "http"
        g.endpoints.append(
            {
                "id": eid,
                "deploymentId": dep_id,
                "type": "internalAPI",
                "protocol": scheme,
                "url": ep.url,
                "authType": "bearer" if ep.auth_required else "none",
                "supportedOperations": ep.operations or [],
                "healthPath": _health_path_for(framework),
            }
        )

    # vector indexes
    for vs in vectors:
        vid = f"v-{_slug(vs.url)}-{vs.db_type}"
        if any(v["id"] == vid for v in g.vector_indexes):
            continue
        # one VectorIndex per collection if known, else one stub
        collections = vs.collections or [vs.db_type]
        for col in collections:
            cid = f"{vid}-{_slug(col)}"
            g.vector_indexes.append(
                {
                    "id": cid,
                    "name": col,
                    "dbType": vs.db_type,
                    "collectionName": col,
                    "embeddingDim": 0,
                }
            )

    # observability layer rendered as tools (with a distinguishing backingService)
    for obs in observability:
        tid = f"t-{obs.kind}-{_slug(obs.url)}"
        if any(t["id"] == tid for t in g.tools):
            continue
        g.tools.append(
            {
                "id": tid,
                "name": f"{obs.kind} @ {obs.url}",
                "description": f"{obs.kind} observability layer",
                "backingService": "observability",
            }
        )

    # containers that exposed ports we never reached still surface as
    # deployments so the user can see something existed.
    for c in containers:
        if c.framework is None:
            continue
        dep_id = f"d-container-{_slug(c.name)}"
        if any(d["id"] == dep_id for d in g.deployments):
            continue
        mid = f"m-container-{_slug(c.image)}"
        if not any(m["id"] == mid for m in g.models):
            g.models.append(
                {
                    "id": mid,
                    "name": c.image,
                    "providerType": _provider_for(c.framework),
                    "architecture": {},
                    "training": {"tags": [c.framework]},
                }
            )
        g.deployments.append(
            {
                "id": dep_id,
                "modelId": mid,
                "environment": "dev",
                "inferenceFramework": _framework_norm(c.framework),
                "resources": {"numReplicas": 1, "gpusPerReplica": 0},
                "configuration": {"extra": {"sourceContainer": c.name}},
            }
        )

    return g


def to_yaml(g: _AssembledGraph, *, header: str | None = None) -> str:
    """Tiny, opinionated YAML emitter for the shapes we produce.

    We don't need full YAML semantics: every value we emit is one of
    str, int, float, bool, list, dict, or None. JSON is a strict YAML
    subset for the kinds of values we write, so the writer is essentially
    `json.dumps` with extra indentation.
    """
    import json

    body = {
        "models": g.models,
        "deployments": g.deployments,
        "endpoints": g.endpoints,
        "vectorIndexes": g.vector_indexes,
        "ragPipelines": g.rag_pipelines,
        "tools": g.tools,
        "agents": g.agents,
        "safetyPolicies": g.safety_policies,
    }
    rendered = json.dumps(body, indent=2, sort_keys=False)
    if header:
        rendered = f"# {header}\n\n" + rendered
    return rendered


# ── helpers ─────────────────────────────────────────────────────────────

def _provider_for(framework: str) -> str:
    if framework in {"openai_compat", "vllm", "tgi", "triton", "llama_cpp", "ollama"}:
        return "custom"
    return "custom"


def _framework_norm(framework: str) -> str:
    return {"openai_compat": "custom"}.get(framework, framework)


def _health_path_for(framework: str) -> str:
    return {
        "ollama": "/api/tags",
        "vllm": "/v1/models",
        "openai_compat": "/v1/models",
        "tgi": "/info",
        "triton": "/v2/health/ready",
        "llama_cpp": "/v1/models",
    }.get(framework, "/v1/models")
