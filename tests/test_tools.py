from types import SimpleNamespace

from mesh.agents.activities import find_activities
from mesh.agents.flights import search_flights
from mesh.orchestrator.tools import check_budget, save_trip_preferences


def test_search_flights_returns_priced_options():
    flights = search_flights.invoke({"origin": "BOM", "destination": "GOI", "date": "2026-12-20"})
    assert flights and all(f["price_usd"] > 0 for f in flights)


def test_find_activities_one_idea_per_interest():
    out = find_activities("Goa", "beaches, food")
    assert len(out["ideas"]) == 2


def test_budget_flow_uses_session_state():
    ctx = SimpleNamespace(state={})
    save_trip_preferences("BOM", "GOI", "2026-12-20", "2026-12-23", 500, "beaches", ctx)
    assert ctx.state["trip"]["budget_usd"] == 500
    over = check_budget([142, 210 * 3], ctx)
    assert over["within_budget"] is False and over["total_usd"] == 772


def test_budget_without_brief():
    assert check_budget([10.5], SimpleNamespace(state={}))["status"] == "no budget saved"
