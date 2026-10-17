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
