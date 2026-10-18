"""Deterministic currency conversion for budgets quoted in local currency."""

# Indicative mid-market rates per 1 USD; refresh from an FX API for production use.
RATES_PER_USD = {
    "USD": 1.0, "INR": 84.0, "EUR": 0.92, "GBP": 0.78,
    "JPY": 150.0, "SGD": 1.34, "IDR": 15800.0, "AED": 3.67,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between currencies: USD, INR, EUR, GBP, JPY, SGD, IDR or AED."""
    src, dst = from_currency.strip().upper(), to_currency.strip().upper()
    missing = [c for c in (src, dst) if c not in RATES_PER_USD]
    if missing:
        return {"error": f"unsupported currency: {', '.join(missing)}",
                "supported": sorted(RATES_PER_USD)}
    rate = RATES_PER_USD[dst] / RATES_PER_USD[src]
    return {"amount": round(amount * rate, 2), "currency": dst, "rate": round(rate, 6)}
