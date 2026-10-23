from mesh.agents import flights
from mesh.orchestrator.agent import build_planner
from mesh.testing.harness import FakeMesh, run_planner
from mesh.testing.scripted_llm import ScriptedLlm, call_many, say

REQUESTS = call_many(
    ("flights_agent", {"request": "Flights from Mumbai to Goa on 2026-12-20"}),
    ("hotels_agent", {"request": "Hotels in Goa from 2026-12-20 for 3 nights"}),
)


async def gemini_down(query: str) -> str:
    raise RuntimeError("503")


async def test_healthy_degraded_and_failed_delegations_are_tallied():
    # flights: LLM down but fallback answers (degraded); hotels: wrong token (failure).
    mesh = FakeMesh(handlers={"flights_agent": gemini_down},
                    fallbacks={"flights_agent": flights.fallback})

    def client(entry):
        return mesh.client(entry, token="wrong" if entry.name == "hotels_agent" else None)

    llm = ScriptedLlm(script=[REQUESTS, say("Partial plan.")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=client)

    _, state = await run_planner(planner, "Plan Goa")

    assert state["delegations"] == {
        "flights_agent": {"calls": 1, "failures": 0, "degraded": 1},
        "hotels_agent": {"calls": 1, "failures": 1, "degraded": 0},
    }


async def test_non_specialist_tools_are_ignored():
    mesh = FakeMesh()
    llm = ScriptedLlm(script=[call_many(("check_budget", {"costs_usd": [1]})), say("ok")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    _, state = await run_planner(planner, "Check")

    assert "delegations" not in state
