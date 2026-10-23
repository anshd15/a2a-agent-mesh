from types import SimpleNamespace

from mesh.agents.activities import find_activities
from mesh.agents.flights import search_flights
from mesh.agents.hotels import format_hotels
from mesh.orchestrator.tools import check_budget, save_trip_preferences


def test_search_flights_returns_priced_options():
    flights = search_flights.invoke({"origin": "BOM", "destination": "GOI", "date": "2026-12-20"})
    assert flights and all(f["price_usd"] > 0 for f in flights)


def test_search_flights_respects_price_cap():
    args = {"origin": "BOM", "destination": "GOI", "date": "2026-12-20"}
    cheapest = search_flights.invoke(args)[0]["price_usd"]
    capped = search_flights.invoke({**args, "max_price_usd": cheapest})
    assert capped and all(f["price_usd"] <= cheapest for f in capped)


def test_hotel_listing_shows_stay_total():
    listing = format_hotels("Goa", "2026-12-20", 3)
    assert listing.startswith("1. ") and "for 3 nights" in listing


def test_find_activities_returns_priced_interest_matches():
    out = find_activities("Goa", "beaches, seafood")
    assert len(out["activities"]) == 4
    assert all(a["matches"] and a["price_usd"] > 0 for a in out["activities"])


def test_budget_flow_uses_session_state():
    ctx = SimpleNamespace(state={})
    save_trip_preferences("BOM", "GOI", "2026-12-20", "2026-12-23", 500, "beaches", ctx)
    assert ctx.state["trip"]["budget_usd"] == 500
    over = check_budget([142, 210 * 3], ctx)
    assert over["within_budget"] is False and over["total_usd"] == 772


def test_budget_without_brief():
    assert check_budget([10.5], SimpleNamespace(state={}))["status"] == "no budget saved"
