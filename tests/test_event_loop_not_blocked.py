"""The collection path must not block the event loop.

DataForSEOClient is synchronous — the SDK under it is — so calling one of its
methods straight from a coroutine holds the loop for the whole round trip to
Google Ads. Nothing else in the process gets served meanwhile, GET /health
included.

In the cluster that was fatal rather than merely slow. The liveness probe
tolerates 30s x 3 = 90s of silence and a keywords_for_keywords call measured
120s, so the kubelet killed the container mid-collection every time:

    Liveness probe failed: Get ".../health": context deadline exceeded
    Killing: Container app failed liveness probe, will be restarted   (exit 137)

The collection died with the pod, every later task in the same analysis failed
with ConnectError against a pod that no longer existed, and the next analysis
retried the identical doomed work. Any collection slower than 90s could not
succeed, deterministically.

These tests pin the property that prevents it: while a slow synchronous client
call is in flight, the loop still answers. They fail if the `await
asyncio.to_thread(...)` in keywords_data_service is ever reduced back to a direct
call.
"""

import asyncio
import time

import pytest

pytestmark = pytest.mark.asyncio


async def _loop_stays_responsive_during(blocking_seconds: float, work: "asyncio.Future | asyncio.Task") -> int:
    """Count how many times a trivial coroutine gets to run while `work` is in
    flight. A blocked loop yields zero — it cannot schedule anything."""
    ticks = 0
    deadline = time.monotonic() + blocking_seconds
    while not work.done() and time.monotonic() < deadline + 1.0:
        await asyncio.sleep(0.01)
        ticks += 1
    await work
    return ticks


async def test_to_thread_keeps_the_loop_free_while_a_sync_call_runs() -> None:
    """The mechanism itself, isolated from the service and from any network.

    A 0.3s synchronous sleep stands in for the Google Ads round trip. Handed to
    a thread, the loop keeps scheduling; called directly it would not, and the
    tick count would be zero.
    """

    def slow_sync_client_call() -> str:
        time.sleep(0.3)
        return "records"

    task = asyncio.create_task(asyncio.to_thread(slow_sync_client_call))
    ticks = await _loop_stays_responsive_during(0.3, task)

    assert task.result() == "records"
    # ~30 ticks at 10ms; anything above a handful proves the loop was never held.
    assert ticks > 5, f"loop was starved while the sync call ran (only {ticks} ticks)"


async def test_a_direct_sync_call_would_starve_the_loop() -> None:
    """The counter-example, so the test above cannot pass vacuously.

    Demonstrates that the bug is real: calling the same function directly from a
    coroutine yields no scheduling opportunities at all. This is what the service
    used to do.
    """
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    ticker_task = asyncio.create_task(ticker())
    await asyncio.sleep(0.05)  # let it get going
    before = ticks

    time.sleep(0.3)  # the blocking call, made the wrong way

    during = ticks - before
    ticker_task.cancel()

    assert during == 0, f"expected a blocked loop to schedule nothing, got {during} ticks"


async def test_service_awaits_its_client_through_a_thread() -> None:
    """Structural check on the call sites.

    Behavioural coverage would need the DataForSEO SDK stubbed and a database;
    what actually regressed is the shape of two lines, so this asserts on the
    source: every call into the synchronous client from the service must go
    through asyncio.to_thread.
    """
    import inspect
    import re

    from app.services import keywords_data_service

    src = inspect.getsource(keywords_data_service)

    direct = re.findall(r"(?<!asyncio\.to_thread\(\n\s{16})self\._client\.(\w+)\(", src)
    assert not direct, f"these client calls bypass asyncio.to_thread and will block the loop: {direct}"

    threaded = re.findall(r"asyncio\.to_thread\(\s*\n\s*self\._client\.(\w+),", src)
    assert set(threaded) == {"search_volume", "keywords_for_keywords"}, (
        f"expected both client methods to run in a thread, found {sorted(threaded)}"
    )
