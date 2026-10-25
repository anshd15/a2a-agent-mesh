"""Hotels specialist built with CrewAI, served over A2A."""
import uvicorn
from a2a.types import AgentSkill
from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

from mesh.common.a2a_server import build_app, build_card
from mesh.config import HOST, HOTELS_PORT, HOTELS_URL, MODEL
from mesh.data.inventory import hotel_options
from mesh.data.parse import parse_trip
from mesh.telemetry import setup_tracing


def format_hotels(city: str, check_in: str, nights: int) -> str:
    return "\n".join(
        f"{i}. {h['name']} - ${h['nightly_usd']}/night, ${h['total_usd']} for {nights} "
        f"nights, {h['rating']} stars"
        for i, h in enumerate(hotel_options(city, check_in, nights), start=1)
    )


@tool("search_hotels")
def search_hotels(city: str, check_in: str, nights: int) -> str:
    """Search hotels in a city for a check-in date (YYYY-MM-DD) and number of nights.

    Results are ranked by rating per dollar and include the total for the stay.
    """
    # Deterministic mock inventory; swap for a real hotels API.
    return format_hotels(city, check_in, nights)


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


async def fallback(query: str) -> str:
    """Rule-based answer straight from the inventory when the CrewAI/Gemini path is down."""
    facts = parse_trip(query)
    if not (facts.destination and facts.start):
        return "Hotels need a city and a check-in date (YYYY-MM-DD)."
    nights = facts.nights or 1
    header = f"Hotels in {facts.destination} from {facts.start}, {nights} night(s):"
    return "\n".join([header, format_hotels(facts.destination, facts.start.isoformat(), nights)])


card = build_card(
    "hotels_agent",
    "Finds best-value hotels (CrewAI).",
    HOTELS_URL,
    [AgentSkill(id="search_hotels", name="Search hotels",
                description="Best-value hotels for given dates, priced for the whole stay",
                tags=["travel", "hotels"],
                examples=["Hotels in Goa from 2026-12-20 for 3 nights",
                          "Hotels in Paris, 2027-05-10 to 2027-05-13"])],
)
app = build_app(card, handle, fallback=fallback)

if __name__ == "__main__":
    setup_tracing("hotels_agent")
    uvicorn.run(app, host=HOST, port=HOTELS_PORT)
