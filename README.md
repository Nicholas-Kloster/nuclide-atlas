# Nuclide Atlas

A self-deployable inspector for an LLM stack you already own. Atlas
reads a YAML inventory of your models, deployments, endpoints, RAG
pipelines, tools, and agents, then renders the whole thing as an
interactive graph. It is meant to live as a sidecar to the stack it
describes, not as an external scanner.

Atlas does not discover infrastructure on its own. It only contacts
endpoints listed in its config file.

## Architecture

Two containers:

| Service          | Port | Purpose                                              |
| ---------------- | ---- | ---------------------------------------------------- |
| `atlas-backend`  | 8000 | FastAPI. Loads the config, runs probes, serves JSON. |
| `atlas-frontend` | 3000 | React + React Flow UI. Proxies `/api/*` to backend.  |

The backend is the source of truth for the schema (`backend/app/models.py`).
Frontend types mirror it in `frontend/src/lib/types.ts`.

## Quick start (docker-compose)

```bash
docker compose up --build
# UI:        http://localhost:3000
# API:       http://localhost:8000/api/graph
# Probes:    http://localhost:8000/api/probe
```

The compose stack mounts `config/atlas.yaml` into the backend container.
Edit that file to describe your own stack, or point `ATLAS_CONFIG` at a
different path.

## API

```
GET  /api/healthz                       liveness
GET  /api/graph                         full inventory
GET  /api/probe                         run probes against every endpoint
GET  /api/metrics/{entityType}/{id}     stubbed metrics snapshot
```

`entityType` is one of `model deployment endpoint ragPipeline vectorIndex tool agent safetyPolicy`.

## Configuration

`config/atlas.yaml` is the entire system description. The example file
ships a small fictional stack so the UI has something to render on
first run:

- 3 models (flagship 13B, embedding, guardrail)
- 4 deployments across `prod` and `stage`
- 4 endpoints (1 public, 3 internal)
- 2 RAG pipelines fed by 2 vector indexes
- 3 tools, 2 agents, 1 safety policy

Strip it and write your own when you are ready.

### Auth tokens for probes

Probe credentials are read from environment variables at startup, never
from the config file. Set one per endpoint id:

```
ATLAS_PROBE_TOKEN_E-FLAGSHIP-PUBLIC=...
```

If no token is set for an endpoint, the probe still runs unauthenticated
and reports the response. A 401 is a useful result.

## Kubernetes

The manifests under `deploy/k8s/` install Atlas into its own namespace.
Edit `configmap.yaml` first to put your real inventory in. Then:

```bash
kubectl apply -k deploy/k8s
kubectl -n nuclide-atlas port-forward svc/atlas-frontend 3000:3000
```

The manifests are a thin skeleton. Add an Ingress, NetworkPolicy, and
real resource limits before exposing this outside the cluster.

## Extending

Adding a new entity type means three edits:

1. New Pydantic model in `backend/app/models.py`, added to `Graph`.
2. Matching TypeScript interface in `frontend/src/lib/types.ts`.
3. Render block in `frontend/src/lib/graphBuild.ts` and a column in `COLUMN`.

Adding a real metrics backend means swapping `backend/app/metrics.py`.
The `MetricsSnapshot` shape is the contract; keep it stable.

## Local development without containers

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ATLAS_CONFIG=../config/atlas.yaml uvicorn app.main:app --reload --port 8000

# frontend (in another shell)
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:8000`, so the UI and API
behave the same in dev and in compose.

## License

MIT.
