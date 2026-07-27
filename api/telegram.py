"""Telegram webhook: принимает один update и отдаёт его диспетчеру aiogram."""

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Модули проекта лежат в корне, а функция запускается из api/ — добавляем корень в путь.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.types import Update  # noqa: E402

from config import BOT_TOKEN  # noqa: E402
from handlers import router  # noqa: E402

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

dispatcher = Dispatcher()
dispatcher.include_router(router)


async def process_update(payload: dict) -> None:
    bot = Bot(token=BOT_TOKEN)
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        header = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not WEBHOOK_SECRET or header != WEBHOOK_SECRET:
            self.send_response(401)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")

        # Telegram повторяет update, если ответ не 200. Ошибку логируем,
        # но подтверждаем приём, иначе он будет слать один и тот же апдейт по кругу.
        try:
            asyncio.run(process_update(payload))
        except Exception as exc:  # noqa: BLE001
            print(f"update failed: {exc!r}", file=sys.stderr)

        self.send_response(200)
        self.end_headers()
