"""Deterministic mock travel inventory.

The same route + date always yields the same options, so demos, tests and evals are
reproducible without a real flights/hotels API. Swap this module for Amadeus / Duffel later.
"""
import hashlib
import random

AIRLINES = [
    "IndiGo", "Air India", "Vistara", "Akasa Air", "Emirates", "Lufthansa", "Singapore Airlines",
]
# (name template, rating, typical nightly USD)
HOTELS = [
    ("Harbour View Inn", 3.9, 70),
    ("Grand {city}", 4.7, 220),
    ("{city} Backpackers", 4.1, 25),
    ("Palm Residency", 4.3, 110),
    ("The Heritage {city}", 4.6, 180),
]


def _rng(*parts: str) -> random.Random:
    key = "|".join(p.strip().lower() for p in parts)
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def flight_options(origin: str, destination: str, date: str, count: int = 4) -> list[dict]:
    """Flight options for a route and date, cheapest first."""
    rng = _rng("flight", origin, destination, date)
    base = rng.randint(60, 400)
    options = []
    for airline in rng.sample(AIRLINES, k=count):
        hour, minute = rng.randint(5, 22), rng.choice([0, 15, 30, 45])
        options.append({
            "airline": airline,
            "depart": f"{date}T{hour:02d}:{minute:02d}",
            "duration_min": rng.randint(60, 600),
            "stops": rng.choice([0, 0, 1]),
            "price_usd": round(base * rng.uniform(0.8, 1.6)),
        })
    return sorted(options, key=lambda o: o["price_usd"])


def hotel_options(city: str, check_in: str, nights: int) -> list[dict]:
    """Hotel options with the total for the stay, best rating-per-dollar first."""
    rng = _rng("hotel", city, check_in)
    options = []
    for template, rating, typical in HOTELS:
        nightly = round(typical * rng.uniform(0.85, 1.3))
        options.append({
            "name": template.format(city=city.strip().title()),
            "rating": rating,
            "nightly_usd": nightly,
            "nights": nights,
            "total_usd": nightly * nights,
        })
    return sorted(options, key=lambda o: o["rating"] / o["nightly_usd"], reverse=True)
