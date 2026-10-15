# Changelog

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
