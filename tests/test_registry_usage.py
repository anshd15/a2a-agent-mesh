import json
from types import SimpleNamespace

from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from mesh.orchestrator.guardrails import MAX_INPUT_CHARS, TOO_LONG, limit_input_length
from mesh.orchestrator.usage import track_usage
from mesh.registry import load_registry


def test_registry_defaults_to_bundled_specialists():
    names = [e.name for e in load_registry(path=None)]
    assert names == ["flights_agent", "hotels_agent", "activities_agent"]


def test_registry_file_adds_and_overrides(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps([
        {"name": "visa_agent", "url": "http://visa:9000", "description": "Visa rules"},
        {"name": "hotels_agent", "url": "http://partner-hotels", "description": "Partner"},
    ]))
    entries = {e.name: e for e in load_registry(str(path))}
    assert entries["visa_agent"].url == "http://visa:9000"
    assert entries["hotels_agent"].url == "http://partner-hotels"
    assert len(entries) == 4


def test_usage_accumulates_tokens_and_cost():
    ctx = SimpleNamespace(state={})
    meta = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=1_000_000, candidates_token_count=100_000
    )
    for _ in range(2):
        track_usage(ctx, LlmResponse(usage_metadata=meta))
    usage = ctx.state["usage"]
    assert usage["calls"] == 2 and usage["input_tokens"] == 2_000_000
    assert usage["cost_usd"] == 0.3 * 2 + 2.5 * 0.2


def test_usage_ignores_responses_without_metadata():
    ctx = SimpleNamespace(state={})
    track_usage(ctx, LlmResponse())
    assert "usage" not in ctx.state


def test_oversized_input_is_refused():
    text = "x" * (MAX_INPUT_CHARS + 1)
    req = LlmRequest(contents=[types.Content(role="user", parts=[types.Part(text=text)])])
    assert limit_input_length(None, req).content.parts[0].text == TOO_LONG
