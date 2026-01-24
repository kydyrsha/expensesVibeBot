import os
from datetime import datetime
from zoneinfo import ZoneInfo


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


BOT_TOKEN = _require_env("BOT_TOKEN")
SUPABASE_URL = _require_env("SUPABASE_URL")
SUPABASE_KEY = _require_env("SUPABASE_KEY")

OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
if OWNER_TELEGRAM_ID:
    try:
        OWNER_TELEGRAM_ID = int(OWNER_TELEGRAM_ID)
    except ValueError as exc:
        raise RuntimeError("OWNER_TELEGRAM_ID must be an integer") from exc

TIMEZONE = os.getenv("TIMEZONE")
if TIMEZONE:
    TZINFO = ZoneInfo(TIMEZONE)
else:
    TZINFO = datetime.now().astimezone().tzinfo
