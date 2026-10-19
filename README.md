# A2A Agent Mesh

A **Google ADK** orchestrator that plans trips by delegating, over the open **A2A (Agent2Agent) protocol**, to specialist agents built in *different frameworks*: LangGraph, CrewAI and ADK itself.

```mermaid
flowchart LR
  U[User] --> G{{Guardrails<br/>length + injection + PII}}
  G --> O[Trip Planner<br/>ADK orchestrator<br/>session state + budget tool]
  O -- A2A JSON-RPC --> F[Flights agent<br/>LangGraph :8001]
  O -- A2A JSON-RPC --> H[Hotels agent<br/>CrewAI :8002]
  O -- A2A JSON-RPC --> A[Activities agent<br/>ADK :8003]
  O -. MESH_REGISTRY .-> X[Any other A2A agent]
  F & H & A -. OTel spans .-> T[(Trace backend)]
```

| Agent | Framework | Port | Skill |
|---|---|---|---|
| `trip_planner` | Google ADK | 8000 (dev UI) | Collects the brief, delegates, checks budget, merges one itinerary |
| `flights_agent` | LangGraph | 8001 | Search & compare flights |
| `hotels_agent` | CrewAI | 8002 | Find best-value hotels |
| `activities_agent` | Google ADK (`to_a2a`) | 8003 | Suggest things to do |

See [docs/architecture.md](docs/architecture.md) for the request sequence and design decisions, and [docs/evaluation.md](docs/evaluation.md) for how quality is measured.

## What it demonstrates
- **Cross-framework interop** - one framework-agnostic `AgentExecutor` wraps LangGraph and CrewAI as A2A servers (a2a-sdk 1.x); ADK agents use `to_a2a` / `RemoteA2aAgent`.
- **Pluggable agents** - add or replace specialists with a JSON registry (`MESH_REGISTRY`, see `registry.example.json`), no code changes.
- **Guardrails** - `before_model_callback`s cap input length, block prompt injection and mask card numbers, emails and phones before anything reaches Gemini.
- **Session state** - the trip brief lives in ADK state (`{trip?}` in the instruction), and budget maths is a deterministic tool, not LLM arithmetic.
- **Structured output** - `finalize_itinerary` validates the plan with Pydantic, stores it in state and renders day-by-day markdown with the budget gap; budgets in INR, EUR and other currencies are converted by a deterministic tool, and trip dates are validated before saving.
- **Cost tracking** - an `after_model_callback` records calls, tokens and estimated USD cost per session.
- **Resilient specialists** - transient errors get jittered-backoff retries, failures come back as readable replies (the planner works around the gap), identical queries hit a TTL cache, a semaphore caps concurrent LLM calls, and `/healthz` gates compose start-up.
- **Distributed tracing** - the orchestrator forwards `traceparent` on every A2A call and each specialist continues the trace (cache hits and errors are tagged on the span); export via OTLP.
- **Reproducible data** - flights and hotels come from a seeded mock inventory, so demos and evals give the same options every run.
- **Service security** - specialists require a shared bearer token (`MESH_TOKEN`); the planner's outbound client masks PII in every delegated A2A message on the wire; cards for private-network specialists are pinned from the registry (ADK only fetches https/loopback cards, so this is also what makes docker compose delegation work). See [SECURITY.md](SECURITY.md).
- **Offline end-to-end tests** - a scripted `BaseLlm` drives the real planner through real A2A JSON-RPC to specialists served in-process: brief saved, delegation, usage, PII masked on the wire, injection short-circuit, pinned cards and token rejection - no API key needed. Key tests are checked to fail when the feature they cover is disabled.
- **Persistent sessions** - `make web` and compose store ADK sessions in SQLite, so trip briefs and usage survive restarts.
- **Evals** - `adk eval` set; an LLM-as-judge over 6 scenarios with repeated runs (mean and stdev) plus a deterministic delegation-coverage metric; a red-team guardrail set; a load-test script with p50/p95/p99; 75 offline tests in CI, including end-to-end runs.
- **Deployable** - one Docker image, `docker compose` locally, `deploy/cloudrun.sh` for Cloud Run.

## Quickstart
```bash
cp .env.example .env              # add your Gemini API key
pip install -e ".[dev,tracing]"
python scripts/run_agents.py      # starts the 3 A2A servers (any OS)
adk web --session_service_uri sqlite+aiosqlite:///./sessions.db mesh   # or: make web
```

Poke a single agent with raw A2A JSON-RPC:
```bash
python scripts/a2a_ping.py http://localhost:8001 "Flights from Mumbai to Goa on 2026-12-20"
```

Check every agent card is reachable:
```bash
python scripts/check_mesh.py      # exits non-zero if any agent is down
```

Dev setup: `pre-commit install` runs ruff lint and format on every commit.

Run everything in containers:
```bash
docker compose up --build         # dev UI on http://localhost:8000
```

Deploy to Cloud Run (Gemini key in Secret Manager as `gemini-api-key`):
```bash
PROJECT=my-project REGION=asia-south1 bash deploy/cloudrun.sh
```

## Tests and evals
```bash
pytest -q                         # 75 offline tests, incl. end-to-end planner -> A2A -> specialist
python scripts/load_test.py http://localhost:8001 --requests 50 --concurrency 10
make eval                         # adk eval (needs API key + agents running)
python eval/judge.py --runs 3     # LLM-as-judge -> eval/results.md (needs API key + agents)
```

Tracing: set `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. a local Jaeger at `http://localhost:4318`) or `MESH_TRACE_CONSOLE=1`.

## Roadmap
- [x] Guardrail callbacks (length, prompt injection, PII)
- [x] Distributed tracing across A2A hops
- [x] `adk eval` set, LLM-as-judge scorer, offline tests
- [x] Docker compose and Cloud Run deploy script
- [x] Pluggable agent registry and per-session cost tracking
- [x] Graceful failures, response cache, concurrency limit, health checks
- [x] Persistent SQLite sessions; judge with repeated runs and delegation coverage
- [x] Retries, structured itinerary, currency tool, red-team set, load test
- [ ] Publish judge scores from a live run
- [ ] Real flight / hotel APIs instead of mock data
- [ ] Streaming responses across A2A
- [x] Shared-token auth between services, outbound PII masking, pinned cards
- [x] Offline end-to-end tests with a scripted LLM
- [ ] Per-agent identities (Cloud Run ID tokens / mTLS) instead of one shared token
