from datetime import UTC, date, datetime

from eingang import clock


def test_system_clock_is_timezone_aware_utc() -> None:
    assert clock.SystemClock().now().tzinfo is UTC


def test_fixed_clock_today_is_the_berlin_date() -> None:
    # 23:30 UTC on 9 March is already 10 March in Berlin.
    fixed = clock.FixedClock(datetime(2026, 3, 9, 23, 30, tzinfo=UTC))
    assert fixed.today() == date(2026, 3, 10)


def test_the_module_clock_can_be_replaced() -> None:
    previous = clock.get_clock()
    fixed = clock.FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    clock.set_clock(fixed)
    try:
        assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)
        assert clock.today() == date(2026, 1, 1)
    finally:
        clock.set_clock(previous)
