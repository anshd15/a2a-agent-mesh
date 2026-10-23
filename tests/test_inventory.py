from mesh.data.inventory import activity_options, flight_options, hotel_options


def test_flights_are_deterministic_and_normalised():
    assert flight_options("BOM", "GOI", "2026-12-20") == flight_options(" bom", "GOI ", "2026-12-20")


def test_flights_change_with_route_or_date():
    base = flight_options("BOM", "GOI", "2026-12-20")
    assert base != flight_options("BOM", "GOI", "2026-12-21")
    assert base != flight_options("DEL", "GOI", "2026-12-20")


def test_flights_are_cheapest_first():
    prices = [f["price_usd"] for f in flight_options("BOM", "GOI", "2026-12-20")]
    assert prices == sorted(prices)
    assert len({f["airline"] for f in flight_options("BOM", "GOI", "2026-12-20")}) == 4


def test_hotel_totals_cover_every_night():
    for hotel in hotel_options("goa", "2026-12-20", 3):
        assert hotel["total_usd"] == hotel["nightly_usd"] * 3
        assert "goa" not in hotel["name"]  # city is title-cased in names


def test_hotels_rank_by_value():
    values = [h["rating"] / h["nightly_usd"] for h in hotel_options("Goa", "2026-12-20", 2)]
    assert values == sorted(values, reverse=True)


def test_activities_put_interest_matches_first_then_cheapest():
    options = activity_options("Goa", "museums, nature", count=8)
    matched = [o for o in options if o["matches"]]
    assert {o["tag"] for o in matched} == {"museums", "nature"}
    assert options[: len(matched)] == matched
    rest = [o["price_usd"] for o in options[len(matched):]]
    assert rest == sorted(rest)


def test_activities_are_deterministic_per_city():
    assert activity_options("Goa", "food") == activity_options(" goa ", "food")
    assert activity_options("Goa", "food") != activity_options("Kochi", "food")
