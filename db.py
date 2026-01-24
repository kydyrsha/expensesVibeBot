from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Tuple

from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL


_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def _raise_on_error(response) -> None:
    error = getattr(response, "error", None)
    if error:
        raise RuntimeError(str(error))


async def add_expense(user_id: int, amount: int, category: str) -> None:
    payload = {
        "user_id": user_id,
        "amount": amount,
        "category": category,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    def _insert():
        return _supabase.table("expenses").insert(payload).execute()

    response = await asyncio.to_thread(_insert)
    _raise_on_error(response)


async def get_weekly_summary(
    user_id: int, start: datetime, end: datetime
) -> Tuple[Dict[str, int], int]:
    start_utc = start.astimezone(timezone.utc).isoformat()
    end_utc = end.astimezone(timezone.utc).isoformat()

    def _fetch():
        return (
            _supabase.table("expenses")
            .select("category,amount")
            .eq("user_id", user_id)
            .gte("created_at", start_utc)
            .lt("created_at", end_utc)
            .execute()
        )

    response = await asyncio.to_thread(_fetch)
    _raise_on_error(response)

    rows = response.data or []
    summary: Dict[str, int] = {}
    total = 0
    for row in rows:
        category = row.get("category")
        amount = int(row.get("amount", 0))
        if category:
            summary[category] = summary.get(category, 0) + amount
            total += amount

    return summary, total
