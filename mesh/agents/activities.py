"""Activities specialist built natively with ADK, exposed via to_a2a."""
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

from mesh.config import ACTIVITIES_PORT, MODEL


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
app = to_a2a(root_agent, port=ACTIVITIES_PORT)

if __name__ == "__main__":
    uvicorn.run(app, port=ACTIVITIES_PORT)
