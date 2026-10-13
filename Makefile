.RECIPEPREFIX = >
.PHONY: install agents web run ping test lint eval up

install:
> pip install -e ".[dev,tracing]"

agents:
> python scripts/run_agents.py

web:
> adk web mesh

run:
> adk run mesh/orchestrator

ping:
> python scripts/a2a_ping.py http://localhost:8001 "Flights from Mumbai to Goa on 2026-12-20"

test:
> pytest -q

lint:
> ruff check .

eval:
> adk eval mesh/orchestrator eval/trip_planner.evalset.json --config_file_path eval/test_config.json --print_detailed_results

up:
> docker compose up --build
