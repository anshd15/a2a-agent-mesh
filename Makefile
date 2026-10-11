.RECIPEPREFIX = >
.PHONY: install agents web run test lint

install:
> pip install -e ".[dev]"

agents:
> python -m mesh.agents.flights & python -m mesh.agents.hotels & python -m mesh.agents.activities & wait

web:
> adk web mesh

run:
> adk run mesh/orchestrator

test:
> pytest -q

lint:
> ruff check .
