"""What one request spent at DataForSEO, in dollars, as DataForSEO reports it.

Every task DataForSEO answers carries the amount it billed for it. That figure
used to reach only the log (DATAFORSEO_COST lines), so the one component able
to say what an analysis's demand data cost was the one nobody reads at analysis
time. The middleware in main.py opens one tally per HTTP request and puts the
total on the response headers; the scoring service adds them into the analysis
and reports them into its trace.

A context variable rather than a return value: the client's methods run in a
worker thread (asyncio.to_thread copies the context, so the thread adds to the
same tally), and threading a number through the service, the repositories and
the response schema would change every signature for a figure none of them use.

Counting never raises. A task that reports no cost counts as a call with
unknown cost, visible in the call count, rather than silently as zero.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class Spend:
    usd: float = 0.0
    calls: int = 0
    # Tasks whose answer carried no cost figure. Kept apart so a total of zero
    # over three calls reads as "not reported" and not as "free".
    calls_without_cost: int = 0


_current: ContextVar[Spend | None] = ContextVar("dataforseo_spend", default=None)


@contextmanager
def collect() -> Iterator[Spend]:
    """Tally the DataForSEO spend of everything that runs inside this block."""
    spend = Spend()
    token = _current.set(spend)
    try:
        yield spend
    finally:
        _current.reset(token)


def current() -> Spend | None:
    """The tally open for this request, or None outside one."""
    return _current.get()


def add(cost: object) -> None:
    """Add one answered DataForSEO task to the current tally, if one is open.

    ``cost`` is the task's own ``cost`` field: a number in USD, or None when
    DataForSEO did not say.
    """
    spend = _current.get()
    if spend is None:
        return
    spend.calls += 1
    if isinstance(cost, bool) or not isinstance(cost, int | float):
        spend.calls_without_cost += 1
        return
    spend.usd += float(cost)


# Header names, shared with the scoring service that reads them.
COST_HEADER = "X-DataForSEO-Cost-USD"
CALLS_HEADER = "X-DataForSEO-Calls"
CALLS_WITHOUT_COST_HEADER = "X-DataForSEO-Calls-Without-Cost"


def headers(spend: Spend) -> dict[str, str]:
    """The tally as response headers; empty when no task was answered."""
    if not spend.calls:
        return {}
    out = {COST_HEADER: f"{spend.usd:.6f}", CALLS_HEADER: str(spend.calls)}
    if spend.calls_without_cost:
        out[CALLS_WITHOUT_COST_HEADER] = str(spend.calls_without_cost)
    return out
