from types import SimpleNamespace

from mesh.orchestrator.itinerary import finalize_itinerary

ITEMS = [
    {"day": 1, "kind": "flight", "description": "IndiGo BOM-GOI 06:10", "cost_usd": 142},
    {"day": 1, "kind": "hotel", "description": "Palm Residency, 3 nights", "cost_usd": 330},
    {"day": 2, "kind": "activity", "description": "Beach day at Palolem"},
]


def test_valid_plan_is_stored_and_rendered_with_budget_gap():
    ctx = SimpleNamespace(state={"trip": {"budget_usd": 600}})
    out = finalize_itinerary("Goa", ITEMS, ctx)
    assert out["status"] == "ok" and out["total_usd"] == 472
    assert "**Day 2**" in out["markdown"] and "$128 under budget" in out["markdown"]
    assert ctx.state["itinerary"]["destination"] == "Goa"


def test_over_budget_is_flagged():
    ctx = SimpleNamespace(state={"trip": {"budget_usd": 400}})
    assert "$72 OVER budget" in finalize_itinerary("Goa", ITEMS, ctx)["markdown"]


def test_invalid_items_are_rejected_without_saving():
    ctx = SimpleNamespace(state={})
    bad = [{"day": 0, "kind": "spaceship", "description": ""}]
    out = finalize_itinerary("Goa", bad, ctx)
    assert out["status"] == "error" and "itinerary" not in ctx.state
