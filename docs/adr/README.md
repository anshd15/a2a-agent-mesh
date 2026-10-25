# Architecture decision records

Short records of the decisions that shape this project: the context, what was decided, and what it costs. New decisions get the next number; superseded ones stay, marked as such.

| # | Decision | Status |
|---|---|---|
| [0001](0001-a2a-between-specialists.md) | Specialists talk A2A, not in-process calls | Accepted |
| [0002](0002-agenttool-over-transfer.md) | Call specialists as `AgentTool`s, not `transfer_to_agent` | Accepted (supersedes the original transfer design) |
| [0003](0003-pin-cards-for-private-networks.md) | Pin agent cards for plain-http private-network specialists | Accepted |
| [0004](0004-specialist-output-is-data.md) | Specialist output is data, never instructions | Accepted |
| [0005](0005-offline-testing-with-scripted-llm.md) | Test whole agent runs offline with a scripted LLM | Accepted |
