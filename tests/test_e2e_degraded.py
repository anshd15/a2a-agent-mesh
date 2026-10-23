"""End to end: the planner still gets real options when a specialist's LLM is down."""
from mesh.agents import flights
from mesh.data.inventory import flight_options
from mesh.orchestrator.agent import build_planner
from mesh.testing.harness import FakeMesh, run_planner, tool_results
from mesh.testing.scripted_llm import ScriptedLlm, call, say


async def gemini_down(query: str) -> str:
    raise RuntimeError("503 model overloaded")


async def test_specialist_outage_degrades_to_inventory_answer_over_a2a():
    mesh = FakeMesh(handlers={"flights_agent": gemini_down},
                    fallbacks={"flights_agent": flights.fallback})
    llm = ScriptedLlm(script=[
        call("flights_agent", request="Flights from Mumbai to Goa on 2026-12-20"),
        say("Here is what I found."),
    ])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    events, _ = await run_planner(planner, "Flights from Mumbai to Goa on 2026-12-20")

    reply = tool_results(events, "flights_agent")[0]["result"]
    cheapest = flight_options("Mumbai", "Goa", "2026-12-20")[0]["price_usd"]
    assert reply.startswith("[degraded mode] Flights Mumbai -> Goa on 2026-12-20:")
    assert f"${cheapest}" in reply
