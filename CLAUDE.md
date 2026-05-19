# Nuclide Atlas: Claude Code Playbook

You are running inside a clone of `nuclide-atlas`. Your job: get the user
to a browser at `http://localhost:3000` showing a graph of their LLM
stack with one command of effort. The user does not edit YAML by hand.

## The one command

```
bin/atlas-bootstrap
```

Bootstrap auto-discovers LLM services (env vars → localhost ports →
docker containers → optionally kubectl), writes `config/atlas.yaml`,
boots the stack via docker compose, and opens the browser.

## Decision tree

1. Run `bin/atlas-bootstrap`. Read the exit code.
2. **Exit 0:** done. Browser should be open. Confirm the page renders
   nodes. Stop here.
3. **Exit 64 (no services found):** discovery hit nothing. Ask the user:
   *"Where is your LLM stack? Paste a base URL, a kubectl context, or
   tell me to spin up the demo."*
   - URL → `bin/atlas-bootstrap --local-host <ip>` if it's another host
     on this machine's network, OR after start, POST to
     `/api/import-url` with the URL.
   - K8s namespace → `bin/atlas-bootstrap --k8s-namespace <ns>`.
   - Demo / "I just want to see it work" → `bin/atlas-demo`. That spawns
     mock services on loopback and re-runs bootstrap.
4. **Exit 65 (docker not available):** tell the user to install Docker
   Desktop / Docker Engine, then re-run. If they refuse, point them at
   the README's "Local development without containers" section.
5. **Exit 66 (port in use):** `bin/atlas-bootstrap --port 3001`.

## What the demo command does

`bin/atlas-demo` boots three stdlib HTTP servers on loopback that mimic
Ollama (11434), vLLM (8000), and Qdrant (6333). Bootstrap finds them
exactly the same way it would find real services. Use this when:

- The user wants to evaluate Atlas before pointing it at production.
- The user has no LLM stack on this machine.
- You need a smoke test.

## What success looks like

- `http://localhost:3000` returns a page (not a connection refused).
- The graph shows at least one Model + one Endpoint node.
- Clicking a node opens the right-hand detail panel.

If the graph is empty after a successful boot, discovery is the
problem, not the UI. Walk back to step 3.

## Do not

- Edit the application code. This is a deploy task, not a development
  task. The user can ask for code changes separately.
- Hand-author `config/atlas.yaml`. Use the bootstrap or the UI's
  `+ Add source` panel.
- Commit `config/atlas.yaml`. The `.gitignore` already excludes it
  because it usually contains real infrastructure URLs.
- Disable the `EXIT_*` non-zero codes. The user (or you, in a future
  session) needs them to branch on.

## How to verify after a fresh `git pull`

```
bin/atlas-bootstrap --dry-run
```

Runs discovery, writes `config/atlas.yaml`, skips docker. Useful for
catching schema drift between discovery output and the Pydantic models.
