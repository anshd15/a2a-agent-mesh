# Security

Please report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab) rather than a public issue.

## What is in place
- **Service auth** - with `MESH_TOKEN` set, every specialist rejects A2A calls without `Authorization: Bearer <token>` (constant-time compare). The agent card and `/healthz` stay public for discovery and probes.
- **PII masking, both directions out** - `before_model_callback`s mask card numbers, emails and phones before Gemini sees them, and the planner's outbound client masks the same patterns in every delegated A2A message before it leaves the process.
- **Pinned agent cards** - specialists on a private network (plain http, non-loopback) get a card built from the trusted registry, so a compromised specialist cannot redirect RPC traffic by editing its card. Over https, ADK fetches the live card and checks its RPC URLs share the card's origin.
- **Prompt-injection guardrail** - checked against `eval/redteam.jsonl` in CI.

These are covered by offline end-to-end tests (`tests/test_e2e*.py`).

## Known limits
- One shared token for the whole mesh, not per-agent identities; rotate it via Secret Manager and prefer Cloud Run ID tokens / mTLS for production.
- Traffic inside the docker compose network is plain http.
- Guardrails are regex-based; `eval/redteam.jsonl` lists phrasings they still miss (`known_gap`).
- PII masking is pattern-based (cards, emails, phones); names and addresses pass through.
