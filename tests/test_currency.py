from mesh.orchestrator.currency import convert_currency


def test_inr_budget_converts_to_usd():
    assert convert_currency(50_400, "inr", "USD") == {"amount": 600.0, "currency": "USD",
                                                      "rate": round(1 / 84, 6)}


def test_round_trip_is_stable():
    eur = convert_currency(100, "USD", "EUR")["amount"]
    assert abs(convert_currency(eur, "EUR", "USD")["amount"] - 100) < 0.01


def test_unknown_currency_is_reported_not_guessed():
    out = convert_currency(10, "USD", "XYZ")
    assert "XYZ" in out["error"] and "INR" in out["supported"]
