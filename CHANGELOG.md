# Changelog

All notable changes to Nuclide Atlas are documented here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## [v0.2.0] - 2026-05-18

### Added: zero-config bootstrap, multi-source ingest, risk, query flow, live pulse

The framing shifts from "hand-author YAML, then render" to "see any LLM
stack as a graph." Three entry points cover the spectrum:

- `bin/atlas-bootstrap`: discover env vars + localhost ports + docker
  + optional k8s, write `config/atlas.yaml`, boot, open browser. Stable
  exit codes (`0`/`64`/`65`/`66`) so CI or Claude Code can branch on
  them.
- `bin/atlas-demo`: spawn mock Ollama/vLLM/Qdrant on loopback, then
  bootstrap. Lets anyone evaluate Atlas in one command with zero real
  infrastructure.
- `+ Add source` modal in the UI: probe a URL, re-run discovery, or
  add extra hosts without editing YAML.

#### Backend

- New `app/discovery/` package (stdlib-only, no `httpx`/`pydantic`
  dependency so the bootstrap CLI runs on a bare `python3`).
- Probes: `env_vars`, `local_ports`, `docker_ps`, `kubectl_get`,
  `url_probe`. Port catalog covers Ollama, vLLM, TGI, Qdrant, Weaviate,
  Milvus, MLflow, Langfuse, Phoenix, Gradio.
- `aimap_shim` delegates URL probes to `aimap` when it is on `PATH`,
  for richer fingerprinting; stdlib probes are the fallback.
- `app/risk.py`: deterministic rule engine. Rules: `exposed.no_auth`,
  `unencrypted.public_http`, `unbounded.max_tokens`,
  `info.large_context`, `no_rerank.high_k`, `open_prompt.no_filters`.
- API additions: `GET /api/risk`, `GET /api/sources`,
  `POST /api/discover`, `POST /api/import-url`.

#### Frontend

- `AddSourceModal`: discovery + URL probe tabs.
- `SearchFilter`: type to highlight matching nodes; everything else
  dims.
- `EmptyState`: quickstart CTAs on a fresh graph.
- `RiskBadges`: severity-colored findings on the detail panel.
- Query Flow animation: click an Agent, click "Trace query," watch a
  request pulse from Agent → safety → RAG → vector → model →
  deployments → endpoints.
- Live Pulse toggle: re-probes every 15 seconds, colors endpoints
  green / amber / red.
- Probe-status and risk overlays as small dots on nodes.

#### Operations

- `.github/workflows/release.yml`: tag push triggers multi-arch
  (linux/amd64, linux/arm64) Docker builds, pushes to ghcr.io, creates
  a GitHub Release with auto-generated notes.
- `CLAUDE.md` playbook at repo root tells Claude Code exactly how to
  self-bootstrap a fresh clone.
- `Makefile` mirrors the same flow for users without Claude.
- Config layout split: `config/atlas.example.yaml` committed,
  `config/atlas.yaml` gitignored (discovered, host-specific).
- Container images:
  `ghcr.io/nicholas-kloster/nuclide-atlas-backend:0.2.0`,
  `ghcr.io/nicholas-kloster/nuclide-atlas-frontend:0.2.0`. Multi-arch.

## [v0.1.0] - 2026-05-18

### Added: initial scaffold

First commit. Self-deployable LLM-stack inspector that reads a YAML
inventory and renders it as an interactive graph.

- Pydantic v2 schema covering Model, Deployment, Endpoint, RagPipeline,
  VectorIndex, Tool, Agent, MetricsSnapshot, SafetyPolicy.
- FastAPI backend serving `/api/graph`, `/api/probe`,
  `/api/metrics/{type}/{id}`, `/api/healthz`.
- Stubbed metrics adapter (deterministic per entity) with Prometheus
  TODO markers.
- Scoped endpoint probes that contact only declared endpoints.
- React + `@xyflow/react` frontend with dagre LR auto-layout, column
  ordering (Endpoints → Deployments → Models → RAG/Tools/Vector →
  Agents), detail panel, layer filter, agent-path highlight.
- `docker-compose.yml` wires backend + frontend; `deploy/k8s/` ships
  Deployments, Services, Kustomization.
- Schema source of truth lives in `backend/app/models.py`; frontend
  mirrors it in `frontend/src/lib/types.ts`.
