from types import SimpleNamespace

from google.adk.models import LlmRequest

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.usage import COST_CAP_REPLY, cost_cap
from mesh.testing.harness import FakeMesh, run_planner, texts_by
from mesh.testing.scripted_llm import ScriptedLlm, call, say


def spent(usd: float):
    return SimpleNamespace(state={"usage": {"cost_usd": usd}})


def test_cap_blocks_only_at_or_above_the_limit():
    enforce = cost_cap(0.10)
    assert enforce(spent(0.05), LlmRequest()) is None
    assert enforce(spent(0.10), LlmRequest()).content.parts[0].text == COST_CAP_REPLY
    assert enforce(SimpleNamespace(state={}), LlmRequest()) is None


def test_zero_disables_the_cap():
    assert cost_cap(0)(spent(99.0), LlmRequest()) is None


async def test_runaway_session_is_stopped_mid_run():
    # Each scripted model call costs $0.00008 (100 in / 20 out tokens at Flash prices),
    # so a $0.0001 cap allows two calls and blocks the third.
    mesh = FakeMesh()
    llm = ScriptedLlm(script=[call("check_budget", costs_usd=[100]),
                              call("check_budget", costs_usd=[200]),
                              say("never reached")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client,
                            cost_cap_usd=0.0001)

    events, state = await run_planner(planner, "Check these costs")

    assert len(llm.requests) == 2
    assert texts_by(events, "trip_planner")[-1] == COST_CAP_REPLY
    assert state["usage"]["calls"] == 2
