from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple


def current_month_range(now: datetime) -> Tuple[datetime, datetime]:
    """[первое число текущего месяца 00:00, now) в таймзоне now."""
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def previous_month_range(now: datetime) -> Tuple[datetime, datetime]:
    """[первое число прошлого месяца, первое число текущего) в таймзоне now."""
    end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (end - timedelta(days=1)).replace(day=1)
    return start, end
