"""Data-driven guardrail eval over eval/redteam.jsonl."""
import json
from pathlib import Path

from google.adk.models import LlmRequest
from google.genai import types

from mesh.orchestrator.guardrails import block_prompt_injection, redact

CASES = [json.loads(line) for line in
         (Path(__file__).parents[1] / "eval" / "redteam.jsonl").read_text().splitlines()
         if line.strip()]


def blocked(text: str) -> bool:
    req = LlmRequest(contents=[types.Content(role="user", parts=[types.Part(text=text)])])
    return block_prompt_injection(None, req) is not None


def test_every_listed_injection_is_blocked():
    misses = [c["text"] for c in CASES if c["expect"] == "block" and not blocked(c["text"])]
    assert not misses, misses


def test_benign_requests_pass_untouched():
    benign = [c["text"] for c in CASES if c["kind"] == "benign"]
    assert not [t for t in benign if blocked(t)]
    assert all(redact(t) == t for t in benign)


def test_pii_is_masked_with_the_right_label():
    for case in (c for c in CASES if c["kind"] == "pii"):
        assert f"[{case['expect']}]" in redact(case["text"]), case["text"]


def test_known_gaps_are_documented():
    """Regex guardrails miss these; if one starts being blocked, promote it to 'block'."""
    gaps = [c["text"] for c in CASES if c["expect"] == "known_gap"]
    assert gaps and not [t for t in gaps if blocked(t)]
