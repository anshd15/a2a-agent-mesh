# 0005 - Test whole agent runs offline with a scripted LLM

**Status:** Accepted

## Context
Unit tests covered tools and callbacks, but nothing exercised the planner, ADK's tool loop, A2A JSON-RPC, auth and the specialists together. Running that against Gemini needs a key, costs money and is non-deterministic, so it would not run in CI.

## Decision
- `ScriptedLlm`, a `BaseLlm` that replays scripted tool calls and answers and records every request the model received.
- `build_planner()` takes the model, registry, HTTP clients and circuit breaker as parameters.
- `FakeMesh` serves fake specialists with the real A2A wrapper and reaches them through the planner's real outbound client over `httpx.ASGITransport` - no sockets.
- Key tests are checked to fail when the feature they cover is disabled.

## Consequences
- Whole-trip runs, parallel fan-out, approval pauses, PII on the wire, injection, outages and the circuit breaker are tested in seconds with no key; the same machinery powers `mesh-demo`.
- The scripted model fixes *what* the LLM decides, so these tests prove the system around the model, not the model's judgement. That is still the job of `adk eval` and the LLM-as-judge, which need a key and are not yet published with real numbers.
