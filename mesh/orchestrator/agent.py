"""ADK trip planner that delegates to remote specialists over A2A."""
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent

from mesh.config import A2A_TIMEOUT_S, MODEL
from mesh.orchestrator.guardrails import block_prompt_injection, limit_input_length, redact_pii
from mesh.orchestrator.tools import check_budget, save_trip_preferences
from mesh.orchestrator.usage import track_usage
from mesh.registry import AgentEntry, load_registry
from mesh.telemetry import traced_async_client


def remote(entry: AgentEntry) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=entry.name,
        description=entry.description,
        agent_card=f"{entry.url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}",
        timeout=A2A_TIMEOUT_S,
        httpx_client=traced_async_client(A2A_TIMEOUT_S),
    )


REGISTRY = load_registry()
ROSTER = "\n".join(f"- {e.name}: {e.description}" for e in REGISTRY)

root_agent = Agent(
    name="trip_planner",
    model=MODEL,
    description="Plans complete trips by coordinating specialist agents.",
    instruction=(
        "You plan trips. First collect origin, destination, dates, budget and interests, "
        "then call save_trip_preferences.\n"
        "Current trip brief: {trip?}\n"
        f"Specialists you can delegate to:\n{ROSTER}\n"
        "Hand each part of the trip to the specialist whose description fits. Before "
        "presenting the itinerary, call check_budget with every quoted cost and flag "
        "anything over budget. Finish with one itinerary and a total."
    ),
    tools=[save_trip_preferences, check_budget],
    before_model_callback=[limit_input_length, block_prompt_injection, redact_pii],
    after_model_callback=track_usage,
    sub_agents=[remote(e) for e in REGISTRY],
)
