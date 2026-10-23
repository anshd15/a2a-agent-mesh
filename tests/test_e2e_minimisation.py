"""Data minimisation: specialists see the planner's focused request, never the conversation."""
from mesh.orchestrator.agent import build_planner
from mesh.testing.harness import Conversation, FakeMesh
from mesh.testing.scripted_llm import ScriptedLlm, call, say


async def test_earlier_personal_details_never_reach_a_specialist():
    mesh = FakeMesh()
    llm = ScriptedLlm(script=[
        say("Thanks, noted."),
        call("flights_agent", request="Flights from Mumbai to Goa on 2026-12-20"),
        say("Here are your flights."),
    ])
    chat = Conversation(build_planner(model=llm, registry=mesh.registry,
                                      client_factory=mesh.client))

    # A passport number is not one of the regex-masked patterns, so only minimisation
    # (not masking) keeps it from leaving the planner.
    await chat.send("I'm Priya, passport P1234567, home address 12 Hill Road, Pune.")
    await chat.send("Find me flights from Mumbai to Goa on 2026-12-20.")

    sent = " ".join(mesh.received["flights_agent"])
    assert sent == "Flights from Mumbai to Goa on 2026-12-20"
    for secret in ("Priya", "P1234567", "Hill Road", "Pune"):
        assert secret not in sent
