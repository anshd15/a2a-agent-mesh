from types import SimpleNamespace

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.memory import (
    KEY,
    MAX_PREFERENCES,
    forget_preferences,
    remember_preference,
)
from mesh.testing.harness import Conversation, FakeMesh
from mesh.testing.scripted_llm import ScriptedLlm, call, say


def test_preferences_are_deduplicated_and_bounded():
    ctx = SimpleNamespace(state={})
    remember_preference("Aisle  seat", ctx)
    remember_preference("vegetarian meals", ctx)
    remember_preference("aisle seat", ctx)  # same preference, moves to newest
    assert ctx.state[KEY] == ["vegetarian meals", "aisle seat"]
    for i in range(MAX_PREFERENCES + 5):
        remember_preference(f"pref {i}", ctx)
    assert len(ctx.state[KEY]) == MAX_PREFERENCES and ctx.state[KEY][-1] == "pref 24"


def test_empty_preference_rejected_and_forget_clears():
    ctx = SimpleNamespace(state={KEY: ["aisle seat"]})
    assert remember_preference("   ", ctx)["status"] == "error"
    forget_preferences(ctx)
    assert ctx.state[KEY] == []


async def test_preference_from_one_trip_reaches_the_next_trip():
    mesh = FakeMesh()
    llm = ScriptedLlm(script=[call("remember_preference", preference="aisle seat"),
                              say("Noted."), say("Planning Tokyo with your preferences.")])
    chat = Conversation(build_planner(model=llm, registry=mesh.registry,
                                      client_factory=mesh.client))

    await chat.send("Plan Goa. I always want an aisle seat.")
    fresh_state = await chat.new_session()  # a different trip, same traveller
    await chat.send("Now plan Tokyo.")

    assert fresh_state[KEY] == ["aisle seat"]
    assert "aisle seat" in llm.requests[-1].config.system_instruction
