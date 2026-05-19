"""Probe output types.

Each probe returns a list of `Found*` records. These are intentionally
loose dataclasses, not Pydantic models — they exist to flow between
probes and the merger without dragging a runtime dependency into the
bootstrap script.

The merger maps `Found*` → the strict Pydantic models in `app.models`
and produces a validated `Graph`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FoundEndpoint:
    """An HTTP-ish endpoint that returned something LLM-shaped."""
    url: str
    framework: str | None = None       # vllm, tgi, ollama, llama_cpp, openai-compat
    provider_label: str | None = None  # human-readable origin (env var name, image, …)
    auth_required: bool = False
    operations: list[str] = field(default_factory=list)  # OpenAI-style ops
    raw_models: list[str] = field(default_factory=list)  # model id list, if known
    source: str = ""                   # which probe emitted this
    error: str | None = None           # populated when probe ran but server misbehaved


@dataclass
class FoundVectorStore:
    url: str
    db_type: str                       # qdrant, weaviate, milvus, ...
    collections: list[str] = field(default_factory=list)
    source: str = ""


@dataclass
class FoundObservability:
    """MLflow / Langfuse / Phoenix etc. — the AI-ops tier."""
    url: str
    kind: str                          # mlflow, langfuse, phoenix
    source: str = ""


@dataclass
class FoundContainer:
    """A docker container that *looks* like an LLM service."""
    name: str
    image: str
    ports: list[int]
    framework: str | None = None
    source: str = "docker"
