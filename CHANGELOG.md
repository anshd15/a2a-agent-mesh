# Changelog

## 0.9.0
- Indirect prompt-injection guard: specialist replies that try to issue instructions or call the planner's tools are quarantined before the model reads them; delegation stats gain a `quarantined` count.
- Fix: PII masking now covers tool results (function responses), not only text parts.
- The ADK activities agent runs inside the shared A2A wrapper (no more `to_a2a`), gaining cache, retries, auth, metrics and a rule-based fallback.
- Prometheus `/metrics` on every specialist (outcomes and latency), token-protected.
- Planner prompt moved to a versioned file; `prompt_version` recorded per session and in judge reports.
- Red-team set extended with specialist-output (indirect) injection cases; demo scene for a compromised specialist. 126 offline tests.

## 0.8.0
- The planner calls specialists as ADK `AgentTool`s instead of `transfer_to_agent`: it keeps control of the turn, fans out in parallel and sends each specialist only a focused request.
- Seeded activities inventory with prices, durations and interest matching.
- Per-session delegation stats (calls, failures, degraded) via `after_tool_callback`.
- Judge counts specialists reached as tool calls.
- New end-to-end tests: a whole trip in one turn with parallel fan-out and approved booking; data minimisation across turns.
- Demo reworked around the one-turn trip and a specialist outage; installed as `mesh-demo`, launcher as `mesh-agents`.

## 0.7.0
- Degraded mode: flights and hotels fall back to rule-based inventory answers when the LLM path fails (trip-fact parser + executor fallback, never cached).
- Per-session cost circuit breaker (`MAX_SESSION_COST_USD`).
- `remember_preference` / `forget_preferences` in ADK `user:` state, shared across a traveller's sessions and read by the planner's instruction.
- `book_trip` behind ADK `require_confirmation`: booking only after human approval; idempotent references.
- `scripts/offline_demo.py` (`make demo`): the whole mesh in ~10s with no API key, smoke-tested.
- Test harness: handler/fallback overrides and a multi-session `Conversation` helper; 99 offline tests.

## 0.6.0
- Fix: docker compose delegation - ADK refuses to fetch plain-http cards from non-loopback hosts, so cards for private-network specialists are now pinned from the registry.
- Shared bearer-token auth (`MESH_TOKEN`) on specialist A2A endpoints; card and /healthz stay public.
- Outbound A2A client masks PII in delegated messages and sends the token and traceparent.
- `build_planner()` factory with injectable model, registry and HTTP clients.
- `ScriptedLlm` and an in-process `FakeMesh` harness; offline end-to-end tests of the full planner -> A2A -> specialist path.
- SECURITY.md rewritten around the new controls and remaining limits.

## 0.5.0
- Jittered exponential-backoff retries for transient specialist errors (`RETRY_ATTEMPTS`).
- `finalize_itinerary`: Pydantic-validated plan, stored in state, rendered as markdown with budget gap.
- `convert_currency` tool and trip date/budget validation.
- Red-team guardrail set (`eval/redteam.jsonl`); injection patterns widened to cover disregard/forget/print variants.
- `scripts/load_test.py` with p50/p95/p99 latency and error rate.
- docs/evaluation.md methodology.

## 0.4.0
- Seeded mock travel inventory: flights cheapest first with a price cap, hotels with stay totals.
- Specialists turn handler failures into readable replies and mark the span as ERROR.
- TTL response cache (`SPECIALIST_CACHE_TTL_S`) and concurrency limit (`MAX_CONCURRENCY`).
- `/healthz` on every specialist; compose waits for healthy specialists.
- Judge: delegation-coverage metric and `--runs N` with stdev.
- Persistent ADK sessions in SQLite (`google-adk[db]`).

## 0.3.0
- Pluggable agent registry (`MESH_REGISTRY`) and configurable A2A timeout.
- Trace context propagated from the orchestrator to every specialist.
- Per-session token and cost tracking; input length guardrail.
- LLM-as-judge itinerary scorer over 6 scenarios.
- Cloud Run deploy script; activities card advertises its public https URL.
- Architecture doc with request sequence and design decisions.

## 0.2.0
- Ported the A2A wrapper to a2a-sdk 1.x (protobuf agent cards, route factories) with v0.3 JSON-RPC compat.
- Guardrail callbacks: prompt-injection block and PII masking.
- Session-state trip brief and deterministic budget tool.
- OpenTelemetry span per A2A hop, OTLP export.
- `adk eval` set, offline tests, Docker compose for the full mesh.
- `scripts/check_mesh.py` health check for all agent cards.

## 0.1.0
- ADK orchestrator delegating to LangGraph, CrewAI and ADK agents over A2A.
