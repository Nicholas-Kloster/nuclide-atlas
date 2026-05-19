"""FastAPI entrypoint.

Read-only:
  GET  /api/healthz                liveness
  GET  /api/graph                  full inventory
  GET  /api/probe                  run probes against every endpoint
  GET  /api/metrics/{type}/{id}    stubbed metrics
  GET  /api/risk                   rule-based findings per entity
  GET  /api/sources                where the current graph came from

Mutating:
  POST /api/discover               re-run discovery and rewrite atlas.yaml
  POST /api/import-url             probe a URL and merge into atlas.yaml
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config_loader import _first_existing, load_graph
from .discovery import run_discovery
from .discovery.probes import url_probe
from .metrics import snapshot
from .models import EntityType, Graph, TimeRange
from .probes import probe_all
from .risk import by_entity, evaluate


app = FastAPI(
    title="Nuclide Atlas",
    description="See any LLM stack as a graph.",
    version="0.2.0",
)

_origins = os.environ.get(
    "ATLAS_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Loaded at first request, refreshed when mutating endpoints succeed.
_GRAPH: Graph | None = None
_GRAPH_PATH: Path | None = None


def _graph() -> Graph:
    global _GRAPH, _GRAPH_PATH
    if _GRAPH is None:
        _GRAPH_PATH = _first_existing()
        _GRAPH = load_graph(_GRAPH_PATH)
    return _GRAPH


def _reload_graph() -> Graph:
    global _GRAPH, _GRAPH_PATH
    _GRAPH = None
    _GRAPH_PATH = None
    return _graph()


def _writable_config_path() -> Path:
    """Resolve a path we're allowed to write to. Falls back to the repo's
    config/atlas.yaml when running outside the container."""
    if _GRAPH_PATH and os.access(_GRAPH_PATH.parent, os.W_OK):
        return _GRAPH_PATH.parent / "atlas.yaml"
    repo_default = Path(__file__).resolve().parents[2] / "config" / "atlas.yaml"
    return repo_default


# ── read-only ───────────────────────────────────────────────────────────

@app.get("/api/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    return _graph().model_dump(by_alias=True, mode="json")


@app.get("/api/probe")
async def get_probe() -> dict[str, Any]:
    results = await probe_all(_graph().endpoints)
    return {"results": results, "count": len(results)}


@app.get("/api/metrics/{entity_type}/{entity_id}")
def get_metrics(
    entity_type: EntityType,
    entity_id: str,
    time_range: TimeRange = TimeRange.last_1h,
) -> dict[str, Any]:
    if not _entity_exists(entity_type, entity_id):
        raise HTTPException(status_code=404, detail="entity not found")
    return snapshot(entity_type, entity_id, time_range).model_dump(
        by_alias=True, mode="json"
    )


@app.get("/api/risk")
def get_risk() -> dict[str, Any]:
    findings = evaluate(_graph())
    grouped = by_entity(findings)
    return {
        "findings": [
            {
                "entityType": f.entity_type,
                "entityId": f.entity_id,
                "ruleId": f.rule_id,
                "severity": f.severity,
                "message": f.message,
            }
            for f in findings
        ],
        "byEntity": {
            key: [
                {
                    "ruleId": f.rule_id,
                    "severity": f.severity,
                    "message": f.message,
                }
                for f in items
            ]
            for key, items in grouped.items()
        },
        "count": len(findings),
    }


@app.get("/api/sources")
def get_sources() -> dict[str, Any]:
    path = _GRAPH_PATH or _first_existing()
    return {
        "path": str(path),
        "exists": path.exists(),
        "name": path.name,
    }


# ── mutating ────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    include_env: bool = True
    include_local: bool = True
    include_docker: bool = True
    include_k8s: bool = False
    extra_hosts: list[str] = []
    k8s_namespace: str | None = None


@app.post("/api/discover")
def post_discover(req: DiscoverRequest | None = None) -> dict[str, Any]:
    req = req or DiscoverRequest()
    hosts = ("127.0.0.1",) + tuple(req.extra_hosts)
    result = run_discovery(
        include_env=req.include_env,
        include_local=req.include_local,
        include_docker=req.include_docker,
        include_k8s=req.include_k8s,
        local_hosts=hosts,
        k8s_namespace=req.k8s_namespace,
    )
    target = _writable_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    result.write_yaml(
        target,
        header=f"generated by /api/discover at "
               f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
    )
    g = _reload_graph()
    return {
        "wrote": str(target),
        "sources_run": result.sources_run,
        "counts": result.counts(),
        "graph_summary": result.node_summary(),
        "models": len(g.models),
        "deployments": len(g.deployments),
        "endpoints": len(g.endpoints),
    }


class ImportUrlRequest(BaseModel):
    url: str


@app.post("/api/import-url")
def post_import_url(req: ImportUrlRequest) -> dict[str, Any]:
    endpoints, vectors, observ = url_probe.run(req.url)
    if not endpoints and not vectors and not observ:
        raise HTTPException(
            status_code=422,
            detail=f"{req.url} did not respond like a known LLM service",
        )
    # Re-run full discovery so the existing graph is preserved.
    result = run_discovery()
    result.endpoints.extend(endpoints)
    result.vectors.extend(vectors)
    result.observability.extend(observ)
    result.sources_run.append(f"url:{req.url}")

    target = _writable_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    result.write_yaml(
        target,
        header=f"generated by /api/import-url for {req.url} at "
               f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
    )
    _reload_graph()
    return {
        "added": {
            "endpoints": [asdict(e) for e in endpoints],
            "vectors": [asdict(v) for v in vectors],
            "observability": [asdict(o) for o in observ],
        },
        "wrote": str(target),
        "graph_summary": result.node_summary(),
    }


# ── helpers ─────────────────────────────────────────────────────────────

def _entity_exists(entity_type: EntityType, entity_id: str) -> bool:
    g = _graph()
    bucket: list[Any] = {
        EntityType.model: g.models,
        EntityType.deployment: g.deployments,
        EntityType.endpoint: g.endpoints,
        EntityType.rag_pipeline: g.rag_pipelines,
        EntityType.vector_index: g.vector_indexes,
        EntityType.tool: g.tools,
        EntityType.agent: g.agents,
        EntityType.safety_policy: g.safety_policies,
    }[entity_type]
    return any(item.id == entity_id for item in bucket)
