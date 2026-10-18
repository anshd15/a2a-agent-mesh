from types import SimpleNamespace

from mesh.orchestrator.tools import save_trip_preferences


def save(start: str, end: str, budget: float = 500):
    ctx = SimpleNamespace(state={})
    return save_trip_preferences("BOM", "GOI", start, end, budget, "beaches", ctx), ctx


def test_valid_brief_records_nights():
    out, ctx = save("2026-12-20", "2026-12-23")
    assert out["status"] == "saved" and ctx.state["trip"]["nights"] == 3


def test_end_before_start_is_rejected_without_saving():
    out, ctx = save("2026-12-23", "2026-12-20")
    assert out["status"] == "error" and "trip" not in ctx.state


def test_bad_format_and_budget_are_rejected():
    assert save("20/12/2026", "2026-12-23")[0]["status"] == "error"
    assert save("2026-12-20", "2026-12-23", budget=0)[0]["status"] == "error"
