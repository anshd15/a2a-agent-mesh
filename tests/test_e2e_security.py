"""End-to-end checks for the private-network and auth paths."""
from mesh.orchestrator.agent import build_planner
from mesh.testing.harness import FakeMesh, run_planner, tool_results
from mesh.testing.scripted_llm import ScriptedLlm, call, say

FLIGHTS = call("flights_agent", request="Flights Mumbai to Goa on 2026-12-20")


async def test_compose_style_url_works_through_a_pinned_card():
    # http://flights:8001 is what docker compose uses; ADK refuses to *fetch* such a card,
    # so the planner must pin one from the registry for delegation to work at all.
    mesh = FakeMesh(urls={"flights_agent": "http://flights:8001"})
    llm = ScriptedLlm(script=[FLIGHTS, say("done")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    events, _ = await run_planner(planner, "Flights Mumbai to Goa on 2026-12-20")

    assert tool_results(events, "flights_agent") == [{"result": "flights_agent options for the trip"}]


async def test_specialist_rejects_a_planner_with_the_wrong_token():
    mesh = FakeMesh()
    llm = ScriptedLlm(script=[FLIGHTS, say("Flights are unavailable right now.")])
    planner = build_planner(model=llm, registry=mesh.registry,
                            client_factory=lambda entry: mesh.client(entry, token="wrong"))

    events, _ = await run_planner(planner, "Flights Mumbai to Goa on 2026-12-20")

    assert mesh.received["flights_agent"] == []  # the handler never ran
    result = str(tool_results(events, "flights_agent"))
    assert "401" in result and "options for the trip" not in result
