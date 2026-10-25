# 0002 - Call specialists as AgentTools, not transfer_to_agent

**Status:** Accepted (supersedes the original sub-agent / transfer design)

## Context
The first version registered the remote specialists as ADK `sub_agents`, so the planner delegated with `transfer_to_agent`. Building the offline end-to-end tests showed the cost: after a transfer the specialist owns the rest of the turn. The planner could not gather flights, hotels and activities and then check the budget and build one itinerary in a single turn. The specialist also received the whole conversation.

## Decision
Wrap each `RemoteA2aAgent` in `AgentTool` and give the planner those tools instead of sub-agents.

## Consequences
- The planner keeps control; independent specialists are called in one model turn and ADK runs them in parallel (three 0.3 s calls finish in ~0.3 s).
- Each specialist receives only the planner's focused request. Earlier personal details never leave the planner (data minimisation), verified end to end.
- Failures come back as tool results the planner can reason about, which made the circuit breaker, delegation stats, reply cap and injection guard possible as `before/after_tool_callback`s.
- Specialists no longer author events in the planner's stream; evals count tool calls instead.
