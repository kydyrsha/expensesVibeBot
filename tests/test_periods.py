from datetime import datetime
from zoneinfo import ZoneInfo

from periods import current_month_range, previous_month_range

TZ = ZoneInfo("Europe/Moscow")


def test_previous_month_range_mid_year():
    now = datetime(2026, 7, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2026, 6, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)


def test_previous_month_range_crosses_year():
    now = datetime(2026, 1, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2025, 12, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2026, 1, 1, 0, 0, tzinfo=TZ)


def test_previous_month_range_after_february():
    now = datetime(2024, 3, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2024, 2, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2024, 3, 1, 0, 0, tzinfo=TZ)


def test_current_month_range_ends_now():
    now = datetime(2026, 7, 15, 14, 30, tzinfo=TZ)
    start, end = current_month_range(now)
    assert start == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)
    assert end == now
