from types import SimpleNamespace

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.booking import book_trip
from mesh.testing.harness import Conversation, FakeMesh, texts_by
from mesh.testing.scripted_llm import ScriptedLlm, call, say

ITEMS = [{"day": 1, "kind": "flight", "description": "IndiGo BOM-GOI", "cost_usd": 142},
         {"day": 1, "kind": "hotel", "description": "Palm Residency", "cost_usd": 330}]


def confirmation_requested(events) -> bool:
    return any(p.function_call and p.function_call.name == "adk_request_confirmation"
               for e in events if e.content for p in e.content.parts or [])


def test_booking_needs_an_itinerary_and_is_idempotent():
    assert book_trip(SimpleNamespace(state={}))["status"] == "error"
    itinerary = {"destination": "Goa", "items": ITEMS}
    first = book_trip(SimpleNamespace(state={"itinerary": itinerary}))
    again = book_trip(SimpleNamespace(state={"itinerary": itinerary}))
    assert first["reference"] == again["reference"] and first["total_usd"] == 472


def planner_chat(final_words: str):
    llm = ScriptedLlm(script=[call("finalize_itinerary", destination="Goa", items=ITEMS),
                              call("book_trip"), say(final_words)])
    mesh = FakeMesh()
    return Conversation(build_planner(model=llm, registry=mesh.registry,
                                      client_factory=mesh.client))


async def test_booking_waits_for_approval_then_books():
    chat = planner_chat("Booked!")
    events = await chat.send("Plan Goa and book it")

    assert confirmation_requested(events)
    assert "booking" not in await chat.state()  # paused: nothing booked yet

    events = await chat.answer_confirmation(events, confirmed=True)
    booking = (await chat.state())["booking"]
    assert booking["reference"].startswith("MESH-") and booking["total_usd"] == 472
    assert texts_by(events, "trip_planner")[-1] == "Booked!"


async def test_declined_booking_never_runs():
    chat = planner_chat("Okay, I have not booked anything.")
    events = await chat.send("Plan Goa and book it")
    events = await chat.answer_confirmation(events, confirmed=False)

    assert "booking" not in await chat.state()
    assert texts_by(events, "trip_planner")[-1] == "Okay, I have not booked anything."
