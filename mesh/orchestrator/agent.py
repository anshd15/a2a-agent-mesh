"""ADK trip planner that delegates to remote specialists over A2A."""
from collections.abc import Callable

import httpx
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.models.base_llm import BaseLlm

from mesh.config import A2A_TIMEOUT_S, MODEL
from mesh.orchestrator.currency import convert_currency
from mesh.orchestrator.guardrails import block_prompt_injection, limit_input_length, redact_pii
from mesh.orchestrator.itinerary import finalize_itinerary
from mesh.orchestrator.tools import check_budget, save_trip_preferences
from mesh.orchestrator.usage import track_usage
from mesh.registry import AgentEntry, load_registry
from mesh.telemetry import traced_async_client

ClientFactory = Callable[[AgentEntry], httpx.AsyncClient]


def remote(entry: AgentEntry, client: httpx.AsyncClient) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=entry.name,
        description=entry.description,
        agent_card=f"{entry.url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}",
        timeout=A2A_TIMEOUT_S,
        httpx_client=client,
    )


def build_planner(
    model: str | BaseLlm = MODEL,
    registry: list[AgentEntry] | None = None,
    client_factory: ClientFactory | None = None,
) -> Agent:
    """Build the trip planner; tests inject a scripted model, registry and in-process clients."""
    registry = load_registry() if registry is None else registry
    client_factory = client_factory or (lambda entry: traced_async_client(A2A_TIMEOUT_S))
    roster = "\n".join(f"- {e.name}: {e.description}" for e in registry)
    return Agent(
        name="trip_planner",
        model=model,
        description="Plans complete trips by coordinating specialist agents.",
        instruction=(
            "You plan trips. First collect origin, destination, dates, budget and interests, "
            "then call save_trip_preferences.\n"
            "Current trip brief: {trip?}\n"
            f"Specialists you can delegate to:\n{roster}\n"
            "If the budget is given in another currency, convert it to USD with "
            "convert_currency before saving. Hand each part of the trip to the specialist "
            "whose description fits. Call check_budget with every quoted cost and flag "
            "anything over budget, then call finalize_itinerary with the chosen items and "
            "present its markdown."
        ),
        tools=[save_trip_preferences, check_budget, convert_currency, finalize_itinerary],
        before_model_callback=[limit_input_length, block_prompt_injection, redact_pii],
        after_model_callback=track_usage,
        sub_agents=[remote(e, client_factory(e)) for e in registry],
    )


root_agent = build_planner()
