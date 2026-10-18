import pytest

from mesh.common.retry import retry_async


def flaky(failures: int, exc: type[Exception] = ConnectionError):
    calls = []

    async def fn():
        calls.append(1)
        if len(calls) <= failures:
            raise exc("transient")
        return "ok"

    return fn, calls


async def test_recovers_after_transient_failures_with_bounded_backoff():
    delays = []

    async def fake_sleep(s):
        delays.append(s)

    fn, calls = flaky(2)
    assert await retry_async(fn, attempts=3, base_delay_s=0.1, sleep=fake_sleep) == "ok"
    assert len(calls) == 3
    assert delays[0] <= 0.1 and delays[1] <= 0.2


async def test_non_transient_errors_are_not_retried():
    fn, calls = flaky(1, ValueError)
    with pytest.raises(ValueError):
        await retry_async(fn, attempts=5)
    assert len(calls) == 1


async def test_gives_up_after_last_attempt():
    async def no_sleep(s):
        return None

    fn, calls = flaky(10, TimeoutError)
    with pytest.raises(TimeoutError):
        await retry_async(fn, attempts=3, sleep=no_sleep)
    assert len(calls) == 3
