"""Месячный отчёт. Общий код для Vercel Cron (app.py) и локального APScheduler."""

from __future__ import annotations

from datetime import datetime

from config import OWNER_TELEGRAM_ID, TZINFO
from db import get_summary
from handlers import format_report
from periods import previous_month_range


async def send_monthly_report(bot) -> str:
    if not OWNER_TELEGRAM_ID:
        return "OWNER_TELEGRAM_ID не задан, отчёт некому слать"

    start_at, end_at = previous_month_range(datetime.now(TZINFO))
    summary, total = await get_summary(OWNER_TELEGRAM_ID, start_at, end_at)
    text = format_report(f"Отчёт за {start_at:%m.%Y}", summary, total)
    await bot.send_message(OWNER_TELEGRAM_ID, text)

    return f"отчёт за {start_at:%m.%Y} отправлен, категорий: {len(summary)}"
