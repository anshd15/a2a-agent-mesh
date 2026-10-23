"""Per-session delegation stats: how often each specialist was called, failed or degraded.

Kept in session state under "delegations", so a slow or flaky specialist is visible per
conversation (and to evals) without digging through traces.
"""
from collections.abc import Callable
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

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
        text = str(tool_response)
        stats = dict(tool_context.state.get("delegations") or {})
        entry = dict(stats.get(tool.name) or {"calls": 0, "failures": 0, "degraded": 0})
        entry["calls"] += 1
        if any(marker in text for marker in FAILURE_MARKERS):
            entry["failures"] += 1
        elif DEGRADED_MARKER in text:
            entry["degraded"] += 1
        stats[tool.name] = entry
        tool_context.state["delegations"] = stats
        return None  # observe only; never rewrite the specialist's answer

    return record
