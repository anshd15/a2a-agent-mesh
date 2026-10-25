"""Per-specialist circuit breaker on the planner side.

After `threshold` consecutive failed delegations a specialist's circuit opens: calls are
answered instantly with an 'unavailable' result instead of waiting on a dead service.
After `cooldown_s` the next call is let through as a trial (half-open); success closes the
circuit, another failure re-opens it. State is per planner process, not per session -
a specialist that is down is down for every traveller.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from mesh.config import BREAKER_COOLDOWN_S, BREAKER_THRESHOLD
from mesh.orchestrator.delegation import FAILURE_MARKERS
from mesh.orchestrator.tool_guard import response_text

OPEN_NOTICE = ("{name} is temporarily unavailable (circuit open after repeated failures). "
               "Continue without it and tell the traveller which part is missing.")


@dataclass
class Circuit:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, specialists: set[str], threshold: int = BREAKER_THRESHOLD,
                 cooldown_s: float = BREAKER_COOLDOWN_S,
                 clock: Callable[[], float] = time.monotonic):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self.clock = clock
        self.circuits = {name: Circuit() for name in specialists}

    def state(self, name: str) -> str:
        circuit = self.circuits[name]
        if circuit.opened_at is None:
            return "closed"
        return "half_open" if self.clock() - circuit.opened_at >= self.cooldown_s else "open"

    def before_tool(self, tool: BaseTool, args: dict[str, Any],
                    tool_context: ToolContext) -> dict | None:
        """before_tool_callback: answer instantly while the circuit is open."""
        if tool.name in self.circuits and self.state(tool.name) == "open":
            return {"result": OPEN_NOTICE.format(name=tool.name), "circuit_open": True}
        return None

    def after_tool(self, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
                   tool_response: Any) -> dict | None:
        """after_tool_callback: count consecutive failures; observe only."""
        circuit = self.circuits.get(tool.name)
        if circuit is None or (isinstance(tool_response, dict) and tool_response.get("circuit_open")):
            return None
        if any(marker in response_text(tool_response) for marker in FAILURE_MARKERS):
            circuit.failures += 1
            if circuit.failures >= self.threshold:
                circuit.opened_at = self.clock()  # open, or re-open after a failed trial
        else:
            circuit.failures, circuit.opened_at = 0, None
        return None
