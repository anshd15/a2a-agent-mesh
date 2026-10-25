"""ADK trip planner that delegates to remote specialists over A2A."""
import ipaddress
from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from a2a.types import AgentCard
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.agent_tool import AgentTool

from mesh.common.a2a_server import build_card
from mesh.config import A2A_TIMEOUT_S, MAX_SESSION_COST_USD, MESH_TOKEN, MODEL
from mesh.orchestrator.booking import book_trip_tool
from mesh.orchestrator.breaker import CircuitBreaker
from mesh.orchestrator.currency import convert_currency
from mesh.orchestrator.delegation import delegation_tracker
from mesh.orchestrator.guardrails import block_prompt_injection, limit_input_length, redact_pii
from mesh.orchestrator.itinerary import finalize_itinerary
from mesh.orchestrator.memory import forget_preferences, remember_preference
from mesh.orchestrator.outbound import outbound_client
from mesh.orchestrator.prompts import load_prompt
from mesh.orchestrator.reply_cap import reply_cap
from mesh.orchestrator.tool_guard import injection_guard
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


PLANNER_PROMPT = load_prompt("planner")


def stamp_prompt_version(callback_context: CallbackContext) -> None:
    """Record which prompt version produced this session, so evals can compare versions."""
    callback_context.state["prompt_version"] = PLANNER_PROMPT.tag


def build_planner(
    model: str | BaseLlm = MODEL,
    registry: list[AgentEntry] | None = None,
    client_factory: ClientFactory | None = None,
    cost_cap_usd: float = MAX_SESSION_COST_USD,
    breaker: CircuitBreaker | None = None,
) -> Agent:
    """Build the trip planner; tests inject a scripted model, registry, in-process clients
    and a circuit breaker with a fake clock."""
    registry = load_registry() if registry is None else registry
    client_factory = client_factory or (lambda entry: outbound_client(A2A_TIMEOUT_S, MESH_TOKEN))
    roster = "\n".join(f"- {e.name}: {e.description}" for e in registry)
    specialists = {e.name for e in registry}
    breaker = breaker or CircuitBreaker(specialists)
    return Agent(
        name="trip_planner",
        model=model,
        description="Plans complete trips by coordinating specialist agents.",
        instruction=PLANNER_PROMPT.render(roster=roster),
        before_agent_callback=stamp_prompt_version,
        # Specialists are tools, not sub-agents: the planner keeps control across
        # delegations, fans out in parallel, and each specialist only sees the request.
        tools=[save_trip_preferences, check_budget, convert_currency, finalize_itinerary,
               remember_preference, forget_preferences, book_trip_tool,
               *(AgentTool(agent=remote(e, client_factory(e))) for e in registry)],
        before_model_callback=[cost_cap(cost_cap_usd), limit_input_length,
                               block_prompt_injection, redact_pii],
        after_model_callback=track_usage,
        before_tool_callback=breaker.before_tool,
        # Order matters: ADK stops at the first callback that returns a value, so the
        # observe-only tracker and breaker run before the guard that may replace the reply.
        after_tool_callback=[delegation_tracker(specialists), breaker.after_tool,
                             injection_guard(specialists), reply_cap(specialists)],
    )


root_agent = build_planner()
