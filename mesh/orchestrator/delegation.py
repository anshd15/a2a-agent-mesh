"""Per-session delegation stats: calls, failures, quarantined and degraded answers.

Kept in session state under "delegations", so a slow or flaky specialist is visible per
conversation (and to evals) without digging through traces.
"""
from collections.abc import Callable
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from mesh.orchestrator.tool_guard import looks_injected, response_text

# What a failed delegation looks like in the tool result: ADK RemoteA2aAgent's error
# texts, and the readable error reply from our own A2A executor.
FAILURE_MARKERS = (
    "A2A request failed",
    "Failed to initialize remote A2A agent",
    "could not complete this request",
)
DEGRADED_MARKER = "[degraded mode]"


def delegation_tracker(specialists: set[str]) -> Callable[..., dict | None]:
    """after_tool_callback that tallies calls, failures and degraded answers per specialist."""

    def record(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
               tool_response: Any) -> dict | None:
        if tool.name not in specialists:
            return None
        text = response_text(tool_response)
        stats = dict(tool_context.state.get("delegations") or {})
        entry = {"calls": 0, "failures": 0, "quarantined": 0, "degraded": 0,
                 "short_circuited": 0, **(stats.get(tool.name) or {})}
        entry["calls"] += 1
        if isinstance(tool_response, dict) and tool_response.get("circuit_open"):
            entry["short_circuited"] += 1  # answered by the circuit breaker, never sent
        elif any(marker in text for marker in FAILURE_MARKERS):
            entry["failures"] += 1
        elif looks_injected(text):
            entry["quarantined"] += 1  # the injection guard withholds this reply
        elif DEGRADED_MARKER in text:
            entry["degraded"] += 1
        stats[tool.name] = entry
        tool_context.state["delegations"] = stats
        return None  # observe only; never rewrite the specialist's answer

    return record
