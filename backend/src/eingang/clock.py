"""The one source of "now" and "today", so tests can fix time without patching libraries."""

from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

# Business dates (due, overdue) are judged in the organisation's time zone (check C08).
BUSINESS_TIME_ZONE = ZoneInfo("Europe/Berlin")


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(BUSINESS_TIME_ZONE).date()


class FixedClock:
    """A clock that stands still at `moment` (UTC) until moved; used by tests."""

    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment

    def today(self) -> date:
        return self.moment.astimezone(BUSINESS_TIME_ZONE).date()


_clock: Clock = SystemClock()


def get_clock() -> Clock:
    return _clock


def set_clock(clock: Clock) -> None:
    global _clock  # replaced only by tests and the worker's test environment
    _clock = clock


def now() -> datetime:
    return _clock.now()


def today() -> date:
    return _clock.today()
