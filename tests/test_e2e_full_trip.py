"""One traveller turn, the whole trip: parallel fan-out, budget, itinerary, approved booking."""
import asyncio
import time

from mesh.agents import flights, hotels
from mesh.data.inventory import activity_options, flight_options, hotel_options
from mesh.orchestrator.agent import build_planner
from mesh.testing.harness import Conversation, FakeMesh, texts_by, tool_results
from mesh.testing.scripted_llm import ScriptedLlm, call, call_many, say

FLIGHT = flight_options("Mumbai", "Goa", "2026-12-20")[0]
HOTEL = hotel_options("Goa", "2026-12-20", 3)[0]
ACTIVITY = activity_options("Goa", "beaches")[0]


async def activities_answer(query: str) -> str:
    return "\n".join(f"- {a['name']}: ${a['price_usd']}" for a in activity_options("Goa", "beaches"))


def timed(spans: dict, name: str, inner):
    async def handler(query: str) -> str:
        start = time.perf_counter()
        await asyncio.sleep(0.2)  # stand-in for an LLM round trip
        reply = await inner(query)
        spans[name] = (start, time.perf_counter())
        return reply

    return handler


async def test_whole_trip_in_one_turn_with_parallel_specialists_and_approval():
    spans: dict[str, tuple[float, float]] = {}
    mesh = FakeMesh(handlers={
        "flights_agent": timed(spans, "flights_agent", flights.fallback),
        "hotels_agent": timed(spans, "hotels_agent", hotels.fallback),
        "activities_agent": timed(spans, "activities_agent", activities_answer),
    })
    items = [
        {"day": 1, "kind": "flight", "description": FLIGHT["airline"], "cost_usd": FLIGHT["price_usd"]},
        {"day": 1, "kind": "hotel", "description": HOTEL["name"], "cost_usd": HOTEL["total_usd"]},
        {"day": 2, "kind": "activity", "description": ACTIVITY["name"],
         "cost_usd": ACTIVITY["price_usd"]},
    ]
    costs = [i["cost_usd"] for i in items]
    llm = ScriptedLlm(script=[
        call("save_trip_preferences", origin="Mumbai", destination="Goa",
             start_date="2026-12-20", end_date="2026-12-23", budget_usd=600, interests="beaches"),
        call_many(
            ("flights_agent", {"request": "Flights from Mumbai to Goa on 2026-12-20"}),
            ("hotels_agent", {"request": "Hotels in Goa from 2026-12-20 for 3 nights"}),
            ("activities_agent", {"request": "Things to do in Goa for beaches"}),
        ),
        call("check_budget", costs_usd=costs),
        call("finalize_itinerary", destination="Goa", items=items),
        call("book_trip"),
        say("Booked. Enjoy Goa!"),
    ])
    chat = Conversation(build_planner(model=llm, registry=mesh.registry,
                                      client_factory=mesh.client))

    events = await chat.send("Plan and book Mumbai to Goa, 20-23 Dec, 600 USD, beaches")

    # All three specialists were in flight at the same time.
    assert max(start for start, _ in spans.values()) < min(end for _, end in spans.values())
    flights_reply = tool_results(events, "flights_agent")[0]["result"]
    assert f"${FLIGHT['price_usd']}" in flights_reply
    budget = tool_results(events, "check_budget")[0]
    assert budget["within_budget"] and budget["total_usd"] == sum(costs)
    assert "booking" not in await chat.state()  # paused for approval

    events = await chat.answer_confirmation(events, confirmed=True)
    state = await chat.state()
    assert state["booking"]["total_usd"] == sum(costs)
    assert texts_by(events, "trip_planner")[-1] == "Booked. Enjoy Goa!"
    assert state["usage"]["calls"] == 6
