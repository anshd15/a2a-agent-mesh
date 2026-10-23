import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "judge", Path(__file__).parents[1] / "eval" / "judge.py"
)
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)

ALL = set(judge.SPECIALISTS)


def result(sid: str, value: int, delegated: set[str] = ALL):
    score = judge.Score(completeness=value, budget_adherence=value, coherence=value,
                        grounding=value, rationale="")
    return judge.Result(sid, score, delegated)


def test_scenarios_are_well_formed():
    scenarios = judge.load_scenarios()
    assert len(scenarios) >= 5
    assert all({"id", "prompt"} <= s.keys() for s in scenarios)
    assert len({s["id"] for s in scenarios}) == len(scenarios)


def test_delegation_coverage_counts_only_expected_specialists():
    assert judge.delegation_coverage({"trip_planner", "flights_agent"}) == 1 / 3
    assert judge.delegation_coverage(ALL | {"trip_planner"}) == 1.0


def test_summary_table_averages_each_column():
    table = judge.summarise([result("a", 4), result("b", 2, {"flights_agent"})])
    assert "| a | 4 | 4 | 4 | 4 | 1.00 |" in table
    assert table.count("**3.00**") == len(judge.CRITERIA)
    assert "**0.67**" in table  # delegation: (1 + 1/3) / 2


def test_stdev_row_only_for_multiple_results():
    assert "stdev" not in judge.summarise([result("a", 4)])
    table = judge.summarise([result("a #1", 5), result("a #2", 3)])
    assert table.splitlines()[-1].startswith("| *stdev* | *1.00* |")


async def test_plan_counts_specialists_reached_as_agent_tools():
    from google.adk.runners import InMemoryRunner

    from mesh.orchestrator.agent import build_planner
    from mesh.testing.harness import FakeMesh
    from mesh.testing.scripted_llm import ScriptedLlm, call_many, say

    mesh = FakeMesh()
    llm = ScriptedLlm(script=[
        call_many(*((name, {"request": "Goa, 2026-12-20"}) for name in judge.SPECIALISTS)),
        say("Your Goa plan."),
    ])
    planner = build_planner(model=llm, registry=mesh.registry, client_factory=mesh.client)

    final, reached = await judge.plan(InMemoryRunner(agent=planner), "Plan Goa")

    assert final == "Your Goa plan."
    assert judge.delegation_coverage(reached) == 1.0
