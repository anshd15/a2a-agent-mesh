"""Hotels specialist built with CrewAI, served over A2A."""
import uvicorn
from a2a.types import AgentSkill
from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

from mesh.common.a2a_server import build_app, build_card
from mesh.config import HOTELS_PORT, MODEL


@tool("search_hotels")
def search_hotels(city: str, check_in: str, nights: int) -> str:
    """Search hotels in a city for a check-in date (YYYY-MM-DD) and number of nights."""
    # TODO: replace mock data with a real hotels API
    return (
        f"1. Harbour View Inn, {city} - $95/night, 4.4 stars\n"
        f"2. The Grand {city} - $210/night, 4.8 stars"
    )


def crew(query: str) -> Crew:
    concierge = Agent(
        role="Hotel concierge",
        goal="Find the best-value hotel for the traveller",
        backstory="A seasoned concierge who balances price, rating and location.",
        tools=[search_hotels],
        llm=LLM(model=f"gemini/{MODEL}"),
    )
    task = Task(description=query, expected_output="Top 2 hotels with price and why",
                agent=concierge)
    return Crew(agents=[concierge], tasks=[task])


async def handle(query: str) -> str:
    return str(await crew(query).kickoff_async())


card = build_card(
    "hotels_agent",
    "Finds best-value hotels (CrewAI).",
    HOTELS_PORT,
    [AgentSkill(id="search_hotels", name="Search hotels",
                description="Find hotels for given dates", tags=["travel", "hotels"])],
)
app = build_app(card, handle)

if __name__ == "__main__":
    uvicorn.run(app, port=HOTELS_PORT)
