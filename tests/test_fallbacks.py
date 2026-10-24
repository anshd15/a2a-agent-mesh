from mesh.agents import flights, hotels
from mesh.data.inventory import flight_options


async def test_flights_fallback_lists_inventory_cheapest_first():
    reply = await flights.fallback("Flights from Mumbai to Goa on 2026-12-20")
    cheapest = flight_options("Mumbai", "Goa", "2026-12-20")[0]
    assert reply.startswith("Flights Mumbai -> Goa on 2026-12-20:")
    assert reply.splitlines()[1].endswith(f"${cheapest['price_usd']}")


async def test_hotels_fallback_prices_the_whole_stay():
    reply = await hotels.fallback("Hotels in Goa, 2026-12-20 to 2026-12-23")
    assert reply.startswith("Hotels in Goa from 2026-12-20, 3 night(s):")
    assert "for 3 nights" in reply


async def test_fallbacks_say_what_is_missing():
    assert "need an origin" in await flights.fallback("cheap flights please")
    assert "need a city" in await hotels.fallback("somewhere warm")


async def test_activities_fallback_matches_interests_from_the_request():
    from mesh.agents import activities

    reply = await activities.fallback("Things to do in Goa for beaches and food")
    assert reply.startswith("Things to do in Goa:")
    assert "Beach" in reply or "food" in reply.lower()
    assert "need a city" in await activities.fallback("fun stuff please")


def test_activities_agent_now_uses_the_shared_wrapper():
    from starlette.testclient import TestClient

    from mesh.agents import activities

    with TestClient(activities.app) as client:
        card = client.get("/.well-known/agent-card.json").json()
        assert card["name"] == "activities_agent"
        assert card["skills"][0]["id"] == "find_activities"


async def test_activities_handler_runs_the_adk_agent_and_its_tool(monkeypatch):
    from mesh.agents import activities
    from mesh.testing.scripted_llm import ScriptedLlm, call, say

    llm = ScriptedLlm(script=[call("find_activities", city="Goa", interests="beaches"),
                              say("Day 1: sunset cruise.")])
    monkeypatch.setattr(activities.root_agent, "model", llm)
    activities.runner.cache_clear()
    try:
        assert await activities.handle("Things to do in Goa for beaches") == "Day 1: sunset cruise."
    finally:
        activities.runner.cache_clear()
    tool_result = llm.requests[-1].contents[-1].parts[0].function_response.response
    assert tool_result["city"] == "Goa" and tool_result["activities"]
