from google.adk.models import LlmRequest
from google.genai import types

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.guardrails import redact_pii
from mesh.testing.harness import FakeMesh, run_planner
from mesh.testing.scripted_llm import ScriptedLlm, call, say


def test_function_responses_are_masked_like_text():
    response = types.FunctionResponse(name="hotels_agent", response={
        "result": "Call +91 98765 43210 or mail desk@grandgoa.com",
        "rooms": [{"contact": "4111 1111 1111 1111"}],
    })
    req = LlmRequest(contents=[types.Content(role="user",
                                             parts=[types.Part(function_response=response)])])
    redact_pii(None, req)
    masked = req.contents[0].parts[0].function_response.response
    assert masked == {"result": "Call [PHONE] or mail [EMAIL]", "rooms": [{"contact": "[CARD]"}]}


async def test_specialist_reply_pii_is_masked_before_the_planner_model_sees_it():
    async def chatty_hotels(query: str) -> str:
        return "Palm Residency $95/night - book via desk@palmgoa.com or +91 98765 43210"

    mesh = FakeMesh(handlers={"hotels_agent": chatty_hotels})
    llm = ScriptedLlm(script=[call("hotels_agent", request="Hotels in Goa from 2026-12-20"),
                              say("Found one.")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    await run_planner(planner, "Hotels in Goa")

    seen = str(llm.requests[-1].contents)
    assert "[EMAIL]" in seen and "[PHONE]" in seen
    assert "desk@palmgoa.com" not in seen and "98765" not in seen
