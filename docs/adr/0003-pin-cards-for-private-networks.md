# 0003 - Pin agent cards for plain-http private-network specialists

**Status:** Accepted

## Context
In docker compose the planner reaches specialists at `http://flights:8001`. ADK only fetches an agent card over https or loopback http, so every delegation failed at card resolution - found by an end-to-end test, not by the compose file looking right.

## Decision
`card_source()` fetches the live card for https and loopback URLs, and otherwise builds ("pins") a card from the trusted registry entry.

## Consequences
- Compose and other private networks work without TLS between containers.
- A compromised specialist cannot redirect the planner's RPC traffic by editing its card, because the planner never reads a card it did not build.
- Pinned cards do not pick up skill changes from the specialist; the registry is the source of truth for description and URL.
- Traffic inside the private network is still plain http (listed in SECURITY.md).
