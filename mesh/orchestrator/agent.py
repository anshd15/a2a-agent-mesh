"""ADK trip planner that delegates to remote specialists over A2A."""
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent

from mesh.config import ACTIVITIES_PORT, FLIGHTS_PORT, HOTELS_PORT, MODEL


def remote(name: str, port: int, description: str) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=name,
        description=description,
        agent_card=f"http://localhost:{port}{AGENT_CARD_WELL_KNOWN_PATH}",
    )


root_agent = Agent(
    name="trip_planner",
    model=MODEL,
    description="Plans complete trips by coordinating specialist agents.",
    instruction=(
        "You plan trips. Collect origin, destination, dates and interests. "
        "Delegate flights to flights_agent, hotels to hotels_agent and things to do "
        "to activities_agent, then merge their answers into one itinerary with a total cost."
    ),
    sub_agents=[
        remote("flights_agent", FLIGHTS_PORT, "Finds and compares flights."),
        remote("hotels_agent", HOTELS_PORT, "Finds best-value hotels."),
        remote("activities_agent", ACTIVITIES_PORT, "Suggests things to do."),
    ],
)
