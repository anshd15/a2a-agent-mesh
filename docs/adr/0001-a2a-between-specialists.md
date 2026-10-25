# 0001 - Specialists talk A2A, not in-process calls

**Status:** Accepted

## Context
The flights, hotels and activities specialists are best built in different frameworks (LangGraph for a ReAct tool loop, CrewAI for a role-based crew, ADK natively). They also scale differently and could be replaced by a partner's agent.

## Decision
Every specialist is an independent A2A server. The ADK planner reaches them through `RemoteA2aAgent` over JSON-RPC; one framework-agnostic `FnExecutor` turns any `async (text) -> text` handler into an A2A server with auth, cache, retries, timeout, fallback, tracing and metrics.

## Consequences
- Frameworks, deploys and scaling are independent; a new agent joins via `MESH_REGISTRY`.
- Every hop is a network call: latency, auth and partial failure become first-class concerns (handled by timeouts, retries, degraded mode and the circuit breaker).
- Cross-service behaviour needs real integration tests, which led to [0005](0005-offline-testing-with-scripted-llm.md).
