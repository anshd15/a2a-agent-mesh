"""End to end: a dead specialist stops being called, then recovers after the cooldown."""
import httpx

from mesh.orchestrator.agent import build_planner
from mesh.orchestrator.breaker import CircuitBreaker
from mesh.orchestrator.outbound import outbound_client
from mesh.testing.harness import Conversation, FakeMesh, tool_results
from mesh.testing.scripted_llm import ScriptedLlm, call, say


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FlakyTransport(httpx.AsyncBaseTransport):
    """Refuses connections while `down`; otherwise forwards to the in-process specialist."""

    def __init__(self, app):
        self.inner = httpx.ASGITransport(app=app)
        self.down = True
        self.requests = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        if self.down:
            raise httpx.ConnectError("connection refused", request=request)
        return await self.inner.handle_async_request(request)


async def test_circuit_opens_skips_the_dead_specialist_and_recovers():
    mesh = FakeMesh()
    flaky = FlakyTransport(mesh.apps["flights_agent"])
    clock = Clock()
    breaker = CircuitBreaker({e.name for e in mesh.registry}, threshold=3, cooldown_s=30,
                             clock=clock)

    def client(entry):
        if entry.name == "flights_agent":
            return outbound_client(10, token=mesh.token, transport=flaky)
        return mesh.client(entry)

    turn = [call("flights_agent", request="Flights from Mumbai to Goa on 2026-12-20"),
            say("Here is what I have.")]
    llm = ScriptedLlm(script=turn * 5)
    chat = Conversation(build_planner(model=llm, registry=mesh.registry, client_factory=client,
                                      breaker=breaker))

    for _ in range(3):  # three real attempts against a dead service
        await chat.send("Flights please")
    assert breaker.state("flights_agent") == "open"
    attempts_so_far = flaky.requests

    events = await chat.send("Flights please")  # circuit open: answered instantly
    assert tool_results(events, "flights_agent")[0]["circuit_open"] is True
    assert flaky.requests == attempts_so_far  # the dead service was not contacted

    clock.now = 30  # cooldown over; the service has recovered
    flaky.down = False
    events = await chat.send("Flights please")  # half-open trial succeeds
    assert tool_results(events, "flights_agent") == [{"result": "flights_agent options for the trip"}]
    assert breaker.state("flights_agent") == "closed"

    stats = (await chat.state())["delegations"]["flights_agent"]
    assert stats["failures"] == 3 and stats["short_circuited"] == 1 and stats["calls"] == 5
