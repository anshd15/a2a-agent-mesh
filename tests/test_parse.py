from datetime import date

import pytest

from mesh.data.parse import parse_trip


@pytest.mark.parametrize(("text", "origin", "destination"), [
    ("Flights from Mumbai to Goa on 2026-12-20", "Mumbai", "Goa"),
    ("Plan Delhi to Tokyo, 2027-03-28 to 2027-04-02", "Delhi", "Tokyo"),
    ("Boston to New York this weekend", "Boston", "New York"),
    ("Find flights New Delhi to Goa", "New Delhi", "Goa"),
])
def test_routes_are_extracted_without_leading_verbs(text, origin, destination):
    facts = parse_trip(text)
    assert (facts.origin, facts.destination) == (origin, destination)


def test_two_dates_give_start_end_and_nights():
    facts = parse_trip("Mumbai to Goa, 2026-12-20 to 2026-12-23")
    assert facts.start == date(2026, 12, 20) and facts.end == date(2026, 12, 23)
    assert facts.nights == 3


def test_hotel_style_request_uses_city_and_explicit_nights():
    facts = parse_trip("Hotels in Goa from 2026-12-20 for 4 nights")
    assert facts.destination == "Goa" and facts.origin is None and facts.nights == 4


def test_missing_and_invalid_facts_come_back_as_none():
    facts = parse_trip("somewhere nice, 2026-13-45")
    assert facts.origin is None and facts.destination is None and facts.start is None
