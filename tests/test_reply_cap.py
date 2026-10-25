from types import SimpleNamespace

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.reply_cap import reply_cap
from mesh.testing.harness import FakeMesh, run_planner
from mesh.testing.scripted_llm import ScriptedLlm, call, say

cap = reply_cap({"hotels_agent"}, max_chars=100)


def run_cap(name: str, text: str):
    return cap(SimpleNamespace(name=name), {}, None, {"result": text})


def test_short_replies_and_other_tools_pass_through():
    assert run_cap("hotels_agent", "x" * 100) is None
    assert run_cap("check_budget", "x" * 10_000) is None


def test_long_replies_are_cut_with_a_note():
    out = run_cap("hotels_agent", "y" * 250)
    assert out["truncated"] is True
    assert out["result"].startswith("y" * 100)
    assert out["result"].endswith("[... 150 characters truncated by the planner ...]")


async def test_a_flooding_specialist_cannot_blow_up_the_planner_context():
    async def flood(query: str) -> str:
        return "Palm Residency " * 20_000  # ~300 KB

    mesh = FakeMesh(handlers={"hotels_agent": flood})
    llm = ScriptedLlm(script=[call("hotels_agent", request="Hotels in Goa from 2026-12-20"),
                              say("Found some options.")])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    await run_planner(planner, "Hotels in Goa")

    seen = llm.requests[-1].contents[-1].parts[0].function_response.response
    assert seen["truncated"] is True
    assert len(seen["result"]) < 7_000
