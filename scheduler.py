from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import OWNER_TELEGRAM_ID, TZINFO
from db import get_summary
from handlers import format_weekly_report


async def _send_weekly_report(bot) -> None:
    if not OWNER_TELEGRAM_ID:
        return

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    summary, total = await get_summary(OWNER_TELEGRAM_ID, start, end)
    text = format_weekly_report(summary, total)
    await bot.send_message(OWNER_TELEGRAM_ID, text)


def start_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZINFO)
    trigger = CronTrigger(day_of_week="sun", hour=20, minute=0)
    scheduler.add_job(_send_weekly_report, trigger, kwargs={"bot": bot})
    scheduler.start()
    return scheduler
