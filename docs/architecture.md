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
  Note over P,A: outbound client: PII masked on the wire, Bearer MESH_TOKEN, traceparent
  P->>P: save_trip_preferences -> state["trip"]
  par one model turn, three AgentTool calls in parallel
    P->>F: A2A message/send: focused request only
    F-->>P: flight options (or [degraded mode] from inventory)
  and
    P->>H: A2A message/send: focused request only
    H-->>P: hotel options
  and
    P->>A: A2A message/send: focused request only
    A-->>P: priced activities
  end
  Note over P: after_tool: stats -> state["delegations"]; injected replies quarantined
  Note over P: before_model: PII masked in tool results too
  P->>P: check_budget(costs) -> within_budget?
  P->>P: finalize_itinerary -> state["itinerary"]
  P-->>U: adk_request_confirmation (book_trip)
  U->>P: approve
  P->>P: book_trip -> state["booking"]
  Note over P: after_model: tokens + cost -> state["usage"]
  P-->>U: one itinerary with total cost
```

## Design decisions

| Decision | Why |
|---|---|
| Specialists as `AgentTool`s, not sub-agents | With `transfer_to_agent` the specialist owns the rest of the turn; as tools the planner keeps control, calls independent specialists in one parallel turn (3 x 0.3s calls finish in ~0.3s in the demo), and sends each only its focused request - data minimisation for free. |
| A2A between agents, not in-process calls | Each specialist can use the framework that suits it, scale independently and be swapped for a third-party agent. |
| One `FnExecutor` for every specialist | LangGraph, CrewAI and the ADK activities agent are each just an `async (text) -> text` handler; the wrapper owns the A2A protocol, cards, auth, cache, retries, fallback, tracing and metrics, so all three behave the same in production. |
| Registry file (`MESH_REGISTRY`) | New or partner agents join the mesh by config, and their descriptions drive delegation. |
| Budget maths in a tool | LLM arithmetic drifts; `check_budget` is exact and testable. |
| Guardrails as `before_model_callback`s | They run on every model call, cost nothing when they pass, and short-circuit without an LLM call when they fire. |
| Trace context over HTTP headers | One trace spans orchestrator and specialists, so slow hops are visible per agent. |
| Failures returned as replies, not failed tasks | The planner can still deliver a partial itinerary and say which piece is missing. |
| Cache and concurrency limit in the executor | Every specialist gets them for free, whatever framework it uses. |
| Shared-token auth in middleware | Card and /healthz stay public for discovery and probes; every RPC needs the token, whatever framework the specialist uses. |
| Mask PII in the outbound transport | Guardrails only see what goes to Gemini; delegated messages leave the process, so masking happens on the wire for every specialist. |
| Pin cards for private-network URLs | ADK only fetches cards over https or loopback http; pinning from the registry makes compose work and stops card-based RPC redirection. |
| `build_planner()` factory | The model, registry and HTTP clients are injectable, so the full planner runs offline in tests with a scripted LLM. |
| Specialist output is data, not instructions | An `after_tool_callback` quarantines replies that try to override instructions or drive the planner's own tools, before the model reads them; the approval gate on `book_trip` backs it up for the social-engineering cases keyword detection misses. |
| PII masked in tool results, not just user text | A specialist reply is model input too, so `redact_pii` rewrites function responses as well. |
| Prometheus metrics per specialist | Outcome counts (ok / cache_hit / degraded / error) and latency histograms are what alerting and SLOs are built on; traces explain individual requests. |
| Prompts as versioned files | The planner prompt lives in `mesh/orchestrator/prompts/planner.md`; each session and judge report records `planner@<version>`, so a score change can be traced to a prompt change. |
| Delegation stats in session state | Calls, failures and degraded answers per specialist are visible per conversation and to evals without opening a trace. |
| Rule-based fallback per specialist | An LLM outage returns inventory-backed options marked `[degraded mode]` instead of an error; never cached, so the LLM path is retried next time. |
| Cost circuit breaker as a callback | A runaway delegation loop stops at `MAX_SESSION_COST_USD` before it becomes a bill, with no change to the model or tools. |
| Preferences in `user:` state | ADK shares `user:`-prefixed state across a traveller's sessions, so memory needs no extra service and shows up in the instruction template. |
| `require_confirmation` on `book_trip` | The one irreversible action pauses for explicit approval; declining means the tool never executes. |
| Seeded mock inventory | Evals compare planner behaviour, not random data, so score changes mean something. |

## Measuring quality

- `pytest` - offline: protocol round trip, guardrails, tools, registry, usage tracking.
- `adk eval` - trajectory and response checks (`eval/trip_planner.evalset.json`).
- `eval/judge.py` - LLM-as-judge on 6 scenarios, scoring completeness, budget adherence, coherence and grounding (1-5), written to `eval/results.md`.
