"""FastAPI entrypoint.

Endpoints:

  GET  /api/graph               full inventory (static + probe-derived overlay)
  GET  /api/probe               run probes against every configured endpoint
  GET  /api/metrics/{type}/{id} stubbed metrics for a single entity
  GET  /api/healthz             liveness ping

Run with:
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config_loader import load_graph
from .metrics import snapshot
from .models import EntityType, Graph, TimeRange
from .probes import probe_all

app = FastAPI(
    title="Nuclide Atlas",
    description="Self-deployable LLM-infrastructure inspector.",
    version="0.1.0",
)

# CORS — frontend dev server defaults to localhost:3000 (Vite); broaden via env.
_origins = os.environ.get(
    "ATLAS_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Loaded once at startup. Re-reading the file on every request would
# defeat the point of a stable graph for the UI to render against.
_GRAPH: Graph | None = None


def _graph() -> Graph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = load_graph()
    return _GRAPH


@app.get("/api/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    """Return the entire inventory. Camelcase aliases preserved."""
    return _graph().model_dump(by_alias=True, mode="json")


@app.get("/api/probe")
async def get_probe() -> dict[str, Any]:
    """Run probes against every declared endpoint, in parallel.

    Returns a dict keyed by endpoint id. Useful for the UI's edge
    colouring (green = reachable, red = unreachable).
    """
    results = await probe_all(_graph().endpoints)
    return {"results": results, "count": len(results)}


@app.get("/api/metrics/{entity_type}/{entity_id}")
def get_metrics(
    entity_type: EntityType,
    entity_id: str,
    time_range: TimeRange = TimeRange.last_1h,
) -> dict[str, Any]:
    """Stubbed metrics for an entity. See metrics.py for the prod TODO."""
    if not _entity_exists(entity_type, entity_id):
        raise HTTPException(status_code=404, detail="entity not found")
    snap = snapshot(entity_type, entity_id, time_range)
    return snap.model_dump(by_alias=True, mode="json")


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
