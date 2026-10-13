"""Activities specialist built natively with ADK, exposed via to_a2a."""
from urllib.parse import urlparse

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

from mesh.config import ACTIVITIES_PORT, ACTIVITIES_URL, HOST, MODEL
from mesh.telemetry import setup_tracing


def find_activities(city: str, interests: str) -> dict:
    """Suggest activities in a city matching comma-separated interests."""
    # TODO: back with Google Places / Search grounding
    ideas = [f"{i.strip().title()} tour in {city}" for i in interests.split(",")]
    return {"city": city, "ideas": ideas}


root_agent = Agent(
    name="activities_agent",
    model=MODEL,
    description="Suggests things to do at a destination.",
    instruction="Use find_activities and return a short, day-by-day list of ideas.",
    tools=[find_activities],
)
# The card advertises the public host so other containers can reach it.
app = to_a2a(root_agent, host=urlparse(ACTIVITIES_URL).hostname, port=ACTIVITIES_PORT)

if __name__ == "__main__":
    setup_tracing("activities_agent")
    uvicorn.run(app, host=HOST, port=ACTIVITIES_PORT)
