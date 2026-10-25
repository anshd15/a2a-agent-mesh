.RECIPEPREFIX = >
# Sessions (trip brief, usage) persist across restarts in a local SQLite file.
SESSION_DB_URI ?= sqlite+aiosqlite:///./sessions.db
.PHONY: install agents web run check ping test lint typecheck eval judge up deploy demo

install:
> pip install -e ".[dev,tracing]"

agents:
> mesh-agents

web:
> adk web --session_service_uri $(SESSION_DB_URI) mesh

run:
> adk run mesh/orchestrator

check:
> python scripts/check_mesh.py

ping:
> python scripts/a2a_ping.py http://localhost:8001 "Flights from Mumbai to Goa on 2026-12-20"

test:
> pytest -q

lint:
> ruff check .

typecheck:
> mypy

eval:
> adk eval mesh/orchestrator eval/trip_planner.evalset.json --config_file_path eval/test_config.json --print_detailed_results

demo:
> mesh-demo

judge:
> python eval/judge.py --runs 3

up:
> docker compose up --build

deploy:
> bash deploy/cloudrun.sh
