from mesh.agents import flights, hotels
from mesh.data.inventory import flight_options


async def test_flights_fallback_lists_inventory_cheapest_first():
    reply = await flights.fallback("Flights from Mumbai to Goa on 2026-12-20")
    cheapest = flight_options("Mumbai", "Goa", "2026-12-20")[0]
    assert reply.startswith("Flights Mumbai -> Goa on 2026-12-20:")
    assert reply.splitlines()[1].endswith(f"${cheapest['price_usd']}")


async def test_hotels_fallback_prices_the_whole_stay():
    reply = await hotels.fallback("Hotels in Goa, 2026-12-20 to 2026-12-23")
    assert reply.startswith("Hotels in Goa from 2026-12-20, 3 night(s):")
    assert "for 3 nights" in reply


async def test_fallbacks_say_what_is_missing():
    assert "need an origin" in await flights.fallback("cheap flights please")
    assert "need a city" in await hotels.fallback("somewhere warm")
