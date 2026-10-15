import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "judge", Path(__file__).parents[1] / "eval" / "judge.py"
)
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)


def score(value: int):
    return judge.Score(completeness=value, budget_adherence=value, coherence=value,
                       grounding=value, rationale="")


def test_scenarios_are_well_formed():
    scenarios = judge.load_scenarios()
    assert len(scenarios) >= 5
    assert all({"id", "prompt"} <= s.keys() for s in scenarios)
    assert len({s["id"] for s in scenarios}) == len(scenarios)


def test_summary_table_averages_each_criterion():
    table = judge.summarise([("a", score(4)), ("b", score(2))])
    assert table.count("**3.00**") == len(judge.CRITERIA)
    assert "| a | 4 | 4 | 4 | 4 |" in table
