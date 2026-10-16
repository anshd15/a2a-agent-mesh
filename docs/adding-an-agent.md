# Adding a specialist agent

Any framework works, as long as you can turn it into `async (text) -> text`.

1. Create `mesh/agents/visa.py`:

```python
import uvicorn
from a2a.types import AgentSkill

from mesh.common.a2a_server import build_app, build_card


async def handle(query: str) -> str:
    return my_framework_agent.run(query)  # LangGraph, CrewAI, plain Python...


card = build_card("visa_agent", "Checks visa and entry rules.", "http://localhost:8004",
                  [AgentSkill(id="visa", name="Visa check", description="Entry rules",
                              tags=["travel"])])
app = build_app(card, handle)

if __name__ == "__main__":
    uvicorn.run(app, port=8004)
```

2. Register it without touching the orchestrator:

```bash
MESH_REGISTRY=registry.example.json adk web mesh
```

3. Verify: `python scripts/check_mesh.py` and `python scripts/a2a_ping.py http://localhost:8004 "Do I need a visa for Japan?"`.

The planner reads each agent's description from the registry, so a clear one-line description is what routes requests to it.
