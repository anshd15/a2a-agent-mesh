from types import SimpleNamespace

from mesh.orchestrator.breaker import CircuitBreaker

FLIGHTS = SimpleNamespace(name="flights_agent")
FAIL = {"result": "A2A request failed: HTTP Error 503"}
OK = {"result": "Flights Mumbai -> Goa ..."}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def breaker(clock: Clock) -> CircuitBreaker:
    return CircuitBreaker({"flights_agent"}, threshold=3, cooldown_s=30, clock=clock)


def outcome(b: CircuitBreaker, response: dict):
    """One delegation: before_tool may short-circuit, after_tool records the result."""
    short = b.before_tool(FLIGHTS, {}, None)
    b.after_tool(FLIGHTS, {}, None, short or response)
    return short


def test_opens_after_consecutive_failures_and_short_circuits():
    clock = Clock()
    b = breaker(clock)
    for _ in range(3):
        assert outcome(b, FAIL) is None
    assert b.state("flights_agent") == "open"
    short = outcome(b, FAIL)
    assert short["circuit_open"] is True and "temporarily unavailable" in short["result"]


def test_success_resets_the_failure_streak():
    b = breaker(Clock())
    for response in (FAIL, FAIL, OK, FAIL, FAIL):
        outcome(b, response)
    assert b.state("flights_agent") == "closed"


def test_half_open_trial_closes_on_success_and_reopens_on_failure():
    clock = Clock()
    b = breaker(clock)
    for _ in range(3):
        outcome(b, FAIL)
    clock.now = 30
    assert b.state("flights_agent") == "half_open"
    assert outcome(b, FAIL) is None  # trial call went through... and failed
    assert b.state("flights_agent") == "open"
    clock.now = 60
    assert outcome(b, OK) is None
    assert b.state("flights_agent") == "closed"


def test_other_tools_are_never_touched():
    b = breaker(Clock())
    other = SimpleNamespace(name="check_budget")
    assert b.before_tool(other, {}, None) is None
    assert b.after_tool(other, {}, None, FAIL) is None
