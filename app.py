"""ASGI-вход для Vercel: webhook Telegram и эндпоинт месячного отчёта.

Vercel собирает Python-проект как одно ASGI-приложение (см. pyproject.toml,
[tool.vercel] entrypoint), поэтому оба маршрута живут здесь, а не в api/*.py.
"""

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from config import BOT_TOKEN
from handlers import router
from reports import send_monthly_report

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
CRON_SECRET = os.getenv("CRON_SECRET")

logger = logging.getLogger(__name__)

app = FastAPI()

dispatcher = Dispatcher()
dispatcher.include_router(router)


@app.post("/api/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if not WEBHOOK_SECRET or x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="bad secret token")

    payload = await request.json()
    bot = Bot(token=BOT_TOKEN)
    try:
        await dispatcher.feed_update(bot, Update.model_validate(payload, context={"bot": bot}))
    except Exception:
        # Telegram повторяет update, пока не получит 200, поэтому ошибку
        # логируем, но приём подтверждаем — иначе один и тот же апдейт по кругу.
        logger.exception("update failed")
    finally:
        await bot.session.close()

    return {"ok": True}


@app.get("/api/cron")
async def monthly_report(authorization: str | None = Header(default=None)) -> dict:
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="bad cron secret")

    bot = Bot(token=BOT_TOKEN)
    try:
        result = await send_monthly_report(bot)
    finally:
        await bot.session.close()

    return {"result": result}
