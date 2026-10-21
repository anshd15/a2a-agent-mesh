"""Pull trip facts out of free text so specialists can answer without an LLM.

Used by the rule-based fallbacks (degraded mode) and the offline demo. Best effort by
design: anything it cannot find comes back as None and the caller says what is missing.
"""
import re
from dataclasses import dataclass
from datetime import date

# Leading words that are capitalised in requests but are never part of a city name.
_STOP = {"plan", "flights", "flight", "find", "book", "show", "hotels", "hotel", "trip",
         "search", "get", "cheap", "cheapest", "for", "the", "a"}
_CITY = r"[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?"
_ROUTE = re.compile(rf"({_CITY})\s+to\s+({_CITY})")
_IN_CITY = re.compile(rf"\bin\s+({_CITY})")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NIGHTS = re.compile(r"\b(\d{1,2})\s+nights?\b", re.IGNORECASE)


@dataclass
class TripFacts:
    origin: str | None = None
    destination: str | None = None
    start: date | None = None
    end: date | None = None
    nights: int | None = None


def _clean(city: str) -> str | None:
    words = city.split()
    while words and words[0].lower() in _STOP:
        words.pop(0)
    return " ".join(words) or None


def parse_trip(text: str) -> TripFacts:
    facts = TripFacts()
    if route := _ROUTE.search(text):
        facts.origin, facts.destination = _clean(route.group(1)), _clean(route.group(2))
    elif city := _IN_CITY.search(text):
        facts.destination = _clean(city.group(1))

    dates = []
    for raw in _DATE.findall(text):
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError:
            continue
    if dates:
        facts.start = dates[0]
    if len(dates) > 1 and dates[1] > dates[0]:
        facts.end = dates[1]
        facts.nights = (dates[1] - dates[0]).days
    elif nights := _NIGHTS.search(text):
        facts.nights = int(nights.group(1))
    return facts
