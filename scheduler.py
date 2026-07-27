from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TZINFO
from reports import send_monthly_report


def start_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZINFO)
    trigger = CronTrigger(day=1, hour=9, minute=0)
    scheduler.add_job(send_monthly_report, trigger, kwargs={"bot": bot})
    scheduler.start()
    return scheduler
