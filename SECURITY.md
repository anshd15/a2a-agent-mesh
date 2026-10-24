# Security

Please report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab) rather than a public issue.

## What is in place
- **Service auth** - with `MESH_TOKEN` set, every specialist rejects A2A calls without `Authorization: Bearer <token>` (constant-time compare). The agent card and `/healthz` stay public for discovery and probes.
- **PII masking everywhere text leaves or enters the model** - `before_model_callback`s mask card numbers, emails and phones in the traveller's messages *and* in tool results before Gemini sees them, and the planner's outbound client masks the same patterns in every delegated A2A message before it leaves the process.
- **Indirect prompt-injection guard** - specialist replies are treated as data: replies that try to override instructions, call the planner's own tools or impersonate a system role are quarantined before the model reads them (`tests/test_e2e_indirect_injection.py`).
- **Pinned agent cards** - specialists on a private network (plain http, non-loopback) get a card built from the trusted registry, so a compromised specialist cannot redirect RPC traffic by editing its card. Over https, ADK fetches the live card and checks its RPC URLs share the card's origin.
- **Prompt-injection guardrail** - checked against `eval/redteam.jsonl` in CI.
- **Human approval for side effects** - `book_trip` uses ADK `require_confirmation`; the run pauses and nothing is booked unless the traveller approves.
- **Spend cap** - `MAX_SESSION_COST_USD` stops model calls for a session once its tracked cost reaches the limit.
- **Right to be forgotten** - `forget_preferences` clears a traveller's stored preferences.
- **Data minimisation** - specialists are called as tools with a focused request, so they never receive the conversation; details shared earlier (names, passport numbers, addresses - which regex masking would miss) stay in the planner.

These are covered by offline end-to-end tests (`tests/test_e2e*.py`).

## Known limits
- One shared token for the whole mesh, not per-agent identities; rotate it via Secret Manager and prefer Cloud Run ID tokens / mTLS for production.
- Traffic inside the docker compose network is plain http.
- Guardrails are regex-based; `eval/redteam.jsonl` lists phrasings they still miss (`known_gap`), including a specialist reply that falsely claims the traveller already approved a booking - which is why `book_trip` always asks the traveller directly.
- PII masking is pattern-based (cards, emails, phones); names and addresses pass through.
