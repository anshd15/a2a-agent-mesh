"""In-process mesh for offline end-to-end runs.

Fake specialists are served by the *real* A2A wrapper (auth, cache, retries, tracing) and
reached through the planner's real outbound client over httpx.ASGITransport - so the whole
planner -> A2A JSON-RPC -> specialist path runs without sockets or an API key.
"""
import httpx
from a2a.types import AgentSkill
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from mesh.common.a2a_server import build_app, build_card
from mesh.orchestrator.outbound import outbound_client
from mesh.registry import AgentEntry

TOKEN = "harness-token"
LOOPBACK_URLS = {
    "flights_agent": "http://127.0.0.1:8001",
    "hotels_agent": "http://127.0.0.1:8002",
    "activities_agent": "http://127.0.0.1:8003",
}


class FakeMesh:
    def __init__(self, urls: dict[str, str] = LOOPBACK_URLS, token: str | None = TOKEN):
        self.token = token
        self.received: dict[str, list[str]] = {name: [] for name in urls}
        self.registry = [AgentEntry(name, url, f"{name} specialist") for name, url in urls.items()]
        self.apps = {name: self._app(name, url) for name, url in urls.items()}

    def _app(self, name: str, url: str):
        async def handler(query: str) -> str:
            self.received[name].append(query)
            return f"{name} options for the trip"

        skill = AgentSkill(id=name, name=name, description=f"{name} specialist", tags=["travel"])
        card = build_card(name, f"{name} specialist", url, [skill])
        return build_app(card, handler, cache_ttl_s=0, token=self.token)

    def client(self, entry: AgentEntry, token: str | None = None) -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=self.apps[entry.name])
        return outbound_client(10, token=token or self.token, transport=transport)


async def run_planner(planner: Agent, text: str) -> tuple[list, dict]:
    """Run one user turn; return every event and the final session state."""
    runner = InMemoryRunner(agent=planner)
    session = await runner.session_service.create_session(app_name=runner.app_name, user_id="u")
    message = types.Content(role="user", parts=[types.Part(text=text)])
    events = [e async for e in runner.run_async(user_id="u", session_id=session.id,
                                                new_message=message)]
    session = await runner.session_service.get_session(app_name=runner.app_name, user_id="u",
                                                       session_id=session.id)
    return events, session.state


def texts_by(events: list, author: str) -> list[str]:
    return [p.text for e in events if e.author == author and e.content
            for p in e.content.parts or [] if p.text]
