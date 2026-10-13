"""ADK trip planner that delegates to remote specialists over A2A."""
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent

from mesh.config import ACTIVITIES_URL, FLIGHTS_URL, HOTELS_URL, MODEL
from mesh.orchestrator.guardrails import block_prompt_injection, redact_pii
from mesh.orchestrator.tools import check_budget, save_trip_preferences


def remote(name: str, base_url: str, description: str) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=name,
        description=description,
        agent_card=f"{base_url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}",
    )


root_agent = Agent(
    name="trip_planner",
    model=MODEL,
    description="Plans complete trips by coordinating specialist agents.",
    instruction=(
        "You plan trips. First collect origin, destination, dates, budget and interests, "
        "then call save_trip_preferences.\n"
        "Current trip brief: {trip?}\n"
        "Delegate flights to flights_agent, hotels to hotels_agent and things to do to "
        "activities_agent. Before presenting the itinerary, call check_budget with every "
        "quoted cost and flag anything over budget. Finish with one itinerary and a total."
    ),
    tools=[save_trip_preferences, check_budget],
    before_model_callback=[block_prompt_injection, redact_pii],
    sub_agents=[
        remote("flights_agent", FLIGHTS_URL, "Finds and compares flights."),
        remote("hotels_agent", HOTELS_URL, "Finds best-value hotels."),
        remote("activities_agent", ACTIVITIES_URL, "Suggests things to do."),
    ],
)
