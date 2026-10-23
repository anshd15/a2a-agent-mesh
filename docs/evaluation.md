# Evaluation methodology

Quality is measured in layers, cheapest and most deterministic first.

| Layer | What it checks | Needs API key | Command |
|---|---|---|---|
| Offline end-to-end | Scripted planner -> real A2A JSON-RPC -> specialist: state, delegation, usage, PII masked on the wire, injection short-circuit, pinned cards, token rejection, degraded mode, cost cap, approval before booking, memory across sessions, a whole trip in one turn with parallel fan-out, data minimisation, delegation stats | No | `pytest tests/test_e2e*.py tests/test_booking.py tests/test_memory.py tests/test_cost_cap.py` |
| Offline demo | The same paths, narrated, as a smoke-tested script | No | `make demo` |
| Unit + protocol tests | Tools, inventory, executor (cache, retry, concurrency, errors), A2A HTTP round trip | No | `pytest -q` |
| Red-team set | Injection block rate, benign false positives, PII labels, documented gaps | No | `pytest tests/test_redteam.py` |
| `adk eval` | Tool trajectory and response match on fixed cases | Yes | `make eval` |
| LLM-as-judge | Completeness, budget adherence, coherence, grounding (1-5) over 6 scenarios | Yes | `python eval/judge.py --runs 3` |
| Delegation coverage | Share of specialists the planner actually called (deterministic) | Yes | reported by the judge |
| Load test | p50/p95/p99 latency and error rate per specialist; cache effect with `--same` | Specialist-dependent | `python scripts/load_test.py URL` |

## Reading the results
- Judge scores are noisy: compare means only when the gap is larger than the reported stdev.
- Mock inventory is seeded, so a score change reflects planner behaviour, not different data.
- A delegation drop with stable judge scores usually means the planner is inventing options instead of asking a specialist; check the grounding score.

## Known limits
- Guardrails are regex-based; `eval/redteam.jsonl` lists phrasings they miss (`known_gap`).
- The judge is the same model family as the planner, which can inflate scores; spot-check `eval/results.md` by hand.
