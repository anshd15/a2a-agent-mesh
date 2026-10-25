"""Activities specialist built natively with ADK, served by the shared A2A wrapper.

The ADK agent runs inside an FnExecutor handler, so this specialist gets the same cache,
retries, concurrency limit, auth, /healthz, tracing and degraded-mode fallback as the
LangGraph and CrewAI ones.
"""
import re
from functools import cache

import uvicorn
from a2a.types import AgentSkill
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from mesh.common.a2a_server import build_app, build_card
from mesh.config import ACTIVITIES_PORT, ACTIVITIES_URL, HOST, MODEL
from mesh.data.inventory import activity_options
from mesh.data.parse import parse_trip
from mesh.telemetry import setup_tracing


def find_activities(city: str, interests: str) -> dict:
    """Suggest priced activities in a city; best matches for the comma-separated interests
    come first, each with its duration in hours."""
    # Deterministic mock inventory; swap for Google Places / Search grounding.
    return {"city": city, "activities": activity_options(city, interests)}


root_agent = Agent(
    name="activities_agent",
    model=MODEL,
    description="Suggests priced things to do at a destination.",
    instruction="Use find_activities and return a short, day-by-day list of ideas with prices.",
    tools=[find_activities],
)


@cache
def runner() -> InMemoryRunner:
    return InMemoryRunner(agent=root_agent, app_name="activities_agent")


async def handle(query: str) -> str:
    """Run the ADK agent for one A2A request, in a fresh session."""
    r = runner()
    session = await r.session_service.create_session(app_name=r.app_name, user_id="a2a")
    message = types.Content(role="user", parts=[types.Part(text=query)])
    final = ""
    async for event in r.run_async(user_id="a2a", session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    return final


async def fallback(query: str) -> str:
    """Rule-based answer straight from the inventory when the ADK/Gemini path is down."""
    city = parse_trip(query).destination
    if not city:
        return "Activities need a city, e.g. 'things to do in Goa'."
    # Every longer word is a candidate interest; the inventory matches them against tags.
    interests = ",".join(w for w in re.findall(r"[a-z]+", query.lower()) if len(w) >= 4)
    lines = [f"- {a['name']} ({a['hours']}h): ${a['price_usd']}"
             for a in activity_options(city, interests)]
    return "\n".join([f"Things to do in {city}:", *lines])


card = build_card(
    "activities_agent",
    "Suggests priced things to do at a destination (Google ADK).",
    ACTIVITIES_URL,
    [AgentSkill(id="find_activities", name="Find activities",
                description="Priced activities matching the traveller's interests",
                tags=["travel", "activities"],
                examples=["Things to do in Goa for beaches and food",
                          "Museums and food in Paris"])],
)
app = build_app(card, handle, fallback=fallback)

if __name__ == "__main__":
    setup_tracing("activities_agent")
    uvicorn.run(app, host=HOST, port=ACTIVITIES_PORT)
