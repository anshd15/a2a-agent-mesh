import pytest
from google.adk.models import LlmRequest

from mesh.testing.scripted_llm import ScriptedLlm, call, say


async def first(llm: ScriptedLlm):
    async for response in llm.generate_content_async(LlmRequest()):
        return response


async def test_responses_are_replayed_in_order_and_requests_recorded():
    llm = ScriptedLlm(script=[call("check_budget", costs_usd=[1, 2]), say("done")])
    tool_turn = await first(llm)
    assert tool_turn.content.parts[0].function_call.name == "check_budget"
    assert (await first(llm)).content.parts[0].text == "done"
    assert len(llm.requests) == 2 and tool_turn.usage_metadata.prompt_token_count == 100


async def test_running_out_of_script_fails_loudly():
    with pytest.raises(AssertionError, match="ran out"):
        await first(ScriptedLlm())
