# Architecture

## Request flow

```mermaid
sequenceDiagram
  actor U as Traveller
  participant P as trip_planner (ADK)
  participant F as flights_agent (LangGraph)
  participant H as hotels_agent (CrewAI)
  participant A as activities_agent (ADK)

  U->>P: "Mumbai to Goa, 20-23 Dec, 600 USD, beaches"
  Note over P: before_model: length guard, injection block, PII mask
  P->>P: save_trip_preferences -> state["trip"]
  P->>F: A2A message/send (+ traceparent)
  F-->>P: flight options
  P->>H: A2A message/send (+ traceparent)
  H-->>P: hotel options
  P->>A: A2A message/send (+ traceparent)
  A-->>P: activity ideas
  P->>P: check_budget(costs) -> within_budget?
  Note over P: after_model: tokens + cost -> state["usage"]
  P-->>U: one itinerary with total cost
```

## Design decisions

| Decision | Why |
|---|---|
| A2A between agents, not in-process calls | Each specialist can use the framework that suits it, scale independently and be swapped for a third-party agent. |
| One `FnExecutor` for non-ADK agents | LangGraph and CrewAI only need an `async (text) -> text` handler; the wrapper owns the A2A protocol, cards and tracing. |
| Registry file (`MESH_REGISTRY`) | New or partner agents join the mesh by config, and their descriptions drive delegation. |
| Budget maths in a tool | LLM arithmetic drifts; `check_budget` is exact and testable. |
| Guardrails as `before_model_callback`s | They run on every model call, cost nothing when they pass, and short-circuit without an LLM call when they fire. |
| Trace context over HTTP headers | One trace spans orchestrator and specialists, so slow hops are visible per agent. |

## Measuring quality

- `pytest` - offline: protocol round trip, guardrails, tools, registry, usage tracking.
- `adk eval` - trajectory and response checks (`eval/trip_planner.evalset.json`).
- `eval/judge.py` - LLM-as-judge on 6 scenarios, scoring completeness, budget adherence, coherence and grounding (1-5), written to `eval/results.md`.
