"""Flights specialist built with LangGraph, served over A2A."""
from functools import cache

import uvicorn
from a2a.types import AgentSkill
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from mesh.common.a2a_server import build_app, build_card
from mesh.config import FLIGHTS_PORT, FLIGHTS_URL, HOST, MODEL
from mesh.data.inventory import flight_options
from mesh.data.parse import parse_trip
from mesh.telemetry import setup_tracing


@tool
def search_flights(
    origin: str, destination: str, date: str, max_price_usd: int | None = None
) -> list[dict]:
    """Search flights from origin to destination on a date (YYYY-MM-DD), cheapest first.

    Pass max_price_usd to drop options above the traveller's limit.
    """
    # Deterministic mock inventory; swap for a real flights API (Amadeus / Duffel).
    options = flight_options(origin, destination, date)
    return [o for o in options if max_price_usd is None or o["price_usd"] <= max_price_usd]


@cache
def graph():
    return create_react_agent(ChatGoogleGenerativeAI(model=MODEL), tools=[search_flights])


async def handle(query: str) -> str:
    result = await graph().ainvoke({"messages": [("user", query)]})
    return result["messages"][-1].content


async def fallback(query: str) -> str:
    """Rule-based answer straight from the inventory when the LangGraph/Gemini path is down."""
    facts = parse_trip(query)
    if not (facts.origin and facts.destination and facts.start):
        return "Flights need an origin, a destination and a date (YYYY-MM-DD)."
    options = flight_options(facts.origin, facts.destination, facts.start.isoformat())
    lines = [f"- {o['airline']} {o['depart']}, {o['duration_min']} min, {o['stops']} stop(s): "
             f"${o['price_usd']}" for o in options]
    header = f"Flights {facts.origin} -> {facts.destination} on {facts.start}:"
    return "\n".join([header, *lines])


card = build_card(
    "flights_agent",
    "Finds and compares flights (LangGraph).",
    FLIGHTS_URL,
    [AgentSkill(id="search_flights", name="Search flights",
                description="Find flights between two cities", tags=["travel", "flights"])],
)
app = build_app(card, handle, fallback=fallback)

if __name__ == "__main__":
    setup_tracing("flights_agent")
    uvicorn.run(app, host=HOST, port=FLIGHTS_PORT)
