from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import OWNER_TELEGRAM_ID, TZINFO
from db import get_summary
from handlers import format_report
from periods import previous_month_range


async def _send_monthly_report(bot) -> None:
    if not OWNER_TELEGRAM_ID:
        return

    start_at, end_at = previous_month_range(datetime.now(TZINFO))
    summary, total = await get_summary(OWNER_TELEGRAM_ID, start_at, end_at)
    title = f"Отчёт за {start_at.strftime('%m.%Y')}"
    await bot.send_message(OWNER_TELEGRAM_ID, format_report(title, summary, total))


def start_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZINFO)
    trigger = CronTrigger(day=1, hour=9, minute=0)
    scheduler.add_job(_send_monthly_report, trigger, kwargs={"bot": bot})
    scheduler.start()
    return scheduler
