# Convenience targets for the non-Claude path. The canonical entry is
# still bin/atlas-bootstrap, but `make up` does the same thing.

.PHONY: up down demo discover dry-run logs lint

up:           ## discover + boot the stack + open browser
	bin/atlas-bootstrap

dry-run:      ## discover + write config; skip docker boot
	bin/atlas-bootstrap --dry-run

down:         ## stop the stack
	docker compose down

demo:         ## spawn mock LLM services on loopback, then bootstrap
	bin/atlas-demo

discover:     ## re-run discovery against the running backend
	curl -s -X POST http://localhost:8000/api/discover | python3 -m json.tool

logs:         ## tail the backend container
	docker compose logs -f atlas-backend

lint:         ## frontend typecheck
	cd frontend && ./node_modules/.bin/tsc --noEmit
