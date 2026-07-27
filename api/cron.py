"""Месячный отчёт. Дёргается Vercel Cron первого числа, см. vercel.json."""

import asyncio
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# Модули проекта лежат в корне, а функция запускается из api/ — добавляем корень в путь.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot  # noqa: E402

from config import BOT_TOKEN, OWNER_TELEGRAM_ID, TZINFO  # noqa: E402
from db import get_summary  # noqa: E402
from handlers import format_report  # noqa: E402
from periods import previous_month_range  # noqa: E402

CRON_SECRET = os.getenv("CRON_SECRET")


async def send_monthly_report() -> str:
    if not OWNER_TELEGRAM_ID:
        return "OWNER_TELEGRAM_ID не задан, отчёт некому слать"

    start_at, end_at = previous_month_range(datetime.now(TZINFO))
    summary, total = await get_summary(OWNER_TELEGRAM_ID, start_at, end_at)
    text = format_report(f"Отчёт за {start_at:%m.%Y}", summary, total)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(OWNER_TELEGRAM_ID, text)
    finally:
        await bot.session.close()

    return f"отчёт за {start_at:%m.%Y} отправлен, позиций: {len(summary)}"


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not CRON_SECRET or self.headers.get("Authorization") != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            return

        result = asyncio.run(send_monthly_report())

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(result.encode("utf-8"))
