"""Static-mode loader.

Reads a YAML or JSON file into a validated `Graph`. The path is taken from
the `ATLAS_CONFIG` env var, defaulting to `/etc/nuclide-atlas/config.yaml`
inside the container and `./config/atlas.yaml` for local runs.

Validation is strict — the Pydantic models have `extra="forbid"`, so a
typo in a field name fails loud at startup instead of silently dropping
data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from .models import Graph

DEFAULT_PATHS = (
    os.environ.get("ATLAS_CONFIG"),
    "/etc/nuclide-atlas/config.yaml",
    str(Path(__file__).resolve().parents[2] / "config" / "atlas.yaml"),
)


def _first_existing() -> Path:
    for candidate in DEFAULT_PATHS:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError(
        "No config file found. Set ATLAS_CONFIG or drop a file at "
        + " or ".join(p for p in DEFAULT_PATHS if p)
    )


def load_graph(path: str | os.PathLike | None = None) -> Graph:
    """Parse config from disk into a `Graph`.

    Accepts YAML (.yaml/.yml) or JSON (.json). The file is expected to use
    camelCase keys to match the spec (`modelId`, `numReplicas`, …); the
    Pydantic models accept both alias and snake_case forms.
    """
    target = Path(path) if path else _first_existing()
    raw = target.read_text()
    if target.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw)
    elif target.suffix == ".json":
        data = json.loads(raw)
    else:
        raise ValueError(f"Unsupported config extension: {target.suffix}")
    if data is None:
        return Graph()
    return Graph.model_validate(data)
