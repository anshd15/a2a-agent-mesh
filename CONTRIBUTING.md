# Contributing

```bash
pip install -e ".[dev,tracing]"
pre-commit install
pytest -q && ruff check .
```

- Keep tests offline: no API key should be needed for `pytest`.
- Anything that changes agent behaviour needs a test, an `adk eval` case or a judge scenario.
- New specialist agents: see [docs/adding-an-agent.md](docs/adding-an-agent.md).
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:` ...).
