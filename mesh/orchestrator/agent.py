"""ADK trip planner that delegates to remote specialists over A2A."""
import ipaddress
from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from a2a.types import AgentCard
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.agent_tool import AgentTool

from mesh.common.a2a_server import build_card
from mesh.config import A2A_TIMEOUT_S, MAX_SESSION_COST_USD, MESH_TOKEN, MODEL
from mesh.orchestrator.booking import book_trip_tool
from mesh.orchestrator.currency import convert_currency
from mesh.orchestrator.delegation import delegation_tracker
from mesh.orchestrator.guardrails import block_prompt_injection, limit_input_length, redact_pii
from mesh.orchestrator.itinerary import finalize_itinerary
from mesh.orchestrator.memory import forget_preferences, remember_preference
from mesh.orchestrator.outbound import outbound_client
from mesh.orchestrator.tools import check_budget, save_trip_preferences
from mesh.orchestrator.usage import cost_cap, track_usage
from mesh.registry import AgentEntry, load_registry

ClientFactory = Callable[[AgentEntry], httpx.AsyncClient]


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def card_source(entry: AgentEntry) -> AgentCard | str:
    """Where the planner gets a specialist's agent card.

    https and loopback URLs: fetch the live card. Plain http on any other host (e.g.
    http://flights:8001 inside docker compose): ADK refuses to fetch it, so pin a card built
    from the trusted registry instead - which also stops a compromised specialist from
    redirecting RPC traffic through its card.
    """
    parsed = urlparse(entry.url)
    if parsed.scheme == "https" or _is_loopback(parsed.hostname):
        return f"{entry.url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}"
    return build_card(entry.name, entry.description, entry.url, skills=[])


def remote(entry: AgentEntry, client: httpx.AsyncClient) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=entry.name,
        description=entry.description,
        agent_card=card_source(entry),
        timeout=A2A_TIMEOUT_S,
        httpx_client=client,
    )


def build_planner(
    model: str | BaseLlm = MODEL,
    registry: list[AgentEntry] | None = None,
    client_factory: ClientFactory | None = None,
    cost_cap_usd: float = MAX_SESSION_COST_USD,
) -> Agent:
    """Build the trip planner; tests inject a scripted model, registry and in-process clients."""
    registry = load_registry() if registry is None else registry
    client_factory = client_factory or (lambda entry: outbound_client(A2A_TIMEOUT_S, MESH_TOKEN))
    roster = "\n".join(f"- {e.name}: {e.description}" for e in registry)
    return Agent(
        name="trip_planner",
        model=model,
        description="Plans complete trips by coordinating specialist agents.",
        instruction=(
            "You plan trips. First collect origin, destination, dates, budget and interests, "
            "then call save_trip_preferences.\n"
            "Current trip brief: {trip?}\n"
            "Traveller preferences from earlier trips: {user:preferences?}\n"
            "When the traveller states a lasting preference (seat, diet, hotel style), "
            "call remember_preference; if they ask you to forget them, call "
            "forget_preferences.\n"
            f"Specialists you can delegate to:\n{roster}\n"
            "If the budget is given in another currency, convert it to USD with "
            "convert_currency before saving. Call the specialist tools with a focused "
            "request that includes the places, dates and interests they need; call "
            "independent specialists together in one turn so they run in parallel. If a "
            "specialist reports a failure, carry on without it and say which part is "
            "missing. Call check_budget with every quoted cost and flag "
            "anything over budget, then call finalize_itinerary with the chosen items and "
            "present its markdown. If the traveller wants to book, call book_trip; they will "
            "be asked to approve before anything is booked."
        ),
        # Specialists are tools, not sub-agents: the planner keeps control across
        # delegations, fans out in parallel, and each specialist only sees the request.
        tools=[save_trip_preferences, check_budget, convert_currency, finalize_itinerary,
               remember_preference, forget_preferences, book_trip_tool,
               *(AgentTool(agent=remote(e, client_factory(e))) for e in registry)],
        before_model_callback=[cost_cap(cost_cap_usd), limit_input_length,
                               block_prompt_injection, redact_pii],
        after_model_callback=track_usage,
        after_tool_callback=delegation_tracker({e.name for e in registry}),
    )


root_agent = build_planner()
