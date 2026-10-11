"""Flights specialist built with LangGraph, served over A2A."""
from functools import cache

import uvicorn
from a2a.types import AgentSkill
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from mesh.common.a2a_server import build_app, build_card
from mesh.config import FLIGHTS_PORT, MODEL


@tool
def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Search flights from origin to destination on a date (YYYY-MM-DD)."""
    # TODO: replace mock data with a real flights API (Amadeus / Duffel)
    return [
        {"airline": "IndiGo", "depart": f"{date}T06:10", "price_usd": 142},
        {"airline": "Vistara", "depart": f"{date}T13:45", "price_usd": 188},
    ]


@cache
def graph():
    return create_react_agent(ChatGoogleGenerativeAI(model=MODEL), tools=[search_flights])


async def handle(query: str) -> str:
    result = await graph().ainvoke({"messages": [("user", query)]})
    return result["messages"][-1].content


card = build_card(
    "flights_agent",
    "Finds and compares flights (LangGraph).",
    FLIGHTS_PORT,
    [AgentSkill(id="search_flights", name="Search flights",
                description="Find flights between two cities", tags=["travel", "flights"])],
)
app = build_app(card, handle)

if __name__ == "__main__":
    uvicorn.run(app, port=FLIGHTS_PORT)
