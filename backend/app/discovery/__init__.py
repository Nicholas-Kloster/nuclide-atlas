"""Atlas discovery — turn unknown LLM infrastructure into a Graph.

The discovery layer is **stdlib-only**, deliberately. It runs as part of
the backend (`POST /api/discover`) and from a standalone bootstrap CLI
(`bin/atlas-bootstrap`). Keeping it free of httpx/Pydantic means a fresh
clone with `python3` and no pip install can still self-bootstrap.

Probes are isolated under `probes/` — each takes the environment as
input and returns a list of `Found*` records. The `merger` collapses
their output into the canonical schema written to `config/atlas.yaml`.
"""

from .runner import DiscoveryResult, run_discovery

__all__ = ["DiscoveryResult", "run_discovery"]
