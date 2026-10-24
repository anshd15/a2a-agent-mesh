import pytest

from mesh.orchestrator.agent import PLANNER_PROMPT, build_planner, root_agent
from mesh.orchestrator.prompts import Prompt, load_prompt
from mesh.testing.harness import FakeMesh, run_planner
from mesh.testing.scripted_llm import ScriptedLlm, say


def test_planner_prompt_is_versioned_and_rendered_into_the_agent():
    prompt = load_prompt("planner")
    assert prompt.version and prompt.tag == f"planner@{prompt.version}"
    assert "[[" not in root_agent.instruction
    for name in ("flights_agent", "hotels_agent", "activities_agent"):
        assert f"- {name}:" in root_agent.instruction
    # ADK state templates must survive rendering untouched.
    assert "{trip?}" in root_agent.instruction and "{user:preferences?}" in root_agent.instruction


def test_unfilled_placeholders_fail_loudly():
    with pytest.raises(ValueError, match="unfilled"):
        Prompt("p", "1", "Hello [[NAME]]").render()


async def test_each_session_records_the_prompt_version():
    mesh = FakeMesh()
    planner = build_planner(model=ScriptedLlm(script=[say("Hi!")]), registry=mesh.registry,
                            client_factory=mesh.client)
    _, state = await run_planner(planner, "Hello")
    assert state["prompt_version"] == PLANNER_PROMPT.tag
