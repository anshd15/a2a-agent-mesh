"""A deterministic stand-in for Gemini so whole agent runs can be tested offline.

Each model call pops the next scripted response; every request is recorded so tests can
assert what the model was (or was not) shown.
"""
from typing import Any

from google.adk.models import LlmRequest, LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.genai import types
from pydantic import Field

USAGE = types.GenerateContentResponseUsageMetadata(prompt_token_count=100,
                                                    candidates_token_count=20)


class ScriptedLlm(BaseLlm):
    model: str = "scripted"
    script: list[Any] = Field(default_factory=list)
    requests: list[Any] = Field(default_factory=list)

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        self.requests.append(llm_request)
        if not self.script:
            raise AssertionError("ScriptedLlm ran out of responses")
        yield self.script.pop(0)


def call(name: str, **args) -> LlmResponse:
    """A model turn that calls one tool (or transfer_to_agent)."""
    part = types.Part(function_call=types.FunctionCall(name=name, args=args))
    return LlmResponse(content=types.Content(role="model", parts=[part]), usage_metadata=USAGE)


def say(text: str) -> LlmResponse:
    """A final text answer."""
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]),
                       usage_metadata=USAGE)


def call_many(*calls: tuple[str, dict]) -> LlmResponse:
    """A model turn with several tool calls, which ADK runs in parallel."""
    parts = [types.Part(function_call=types.FunctionCall(name=name, args=args))
             for name, args in calls]
    return LlmResponse(content=types.Content(role="model", parts=parts), usage_metadata=USAGE)
