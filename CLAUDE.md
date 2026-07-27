# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt httpx
.venv/bin/python -m pytest -q          # all tests
.venv/bin/python -m pytest tests/test_periods.py::test_previous_month_range_crosses_year -v
python bot.py                          # local run via long polling (see "Two run modes")
vercel crons run /api/cron             # fire the monthly report by hand, production only
```

`httpx` is only needed if you drive the routes through `fastapi.testclient`. No linter or CI is configured. Tests cover `periods.py` only — see "Testing posture" below.

Required environment variables (validated at import time in `config.py`, missing ones raise on startup): `BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY` (Supabase **service_role** key — the table has RLS enabled with no policies, so the anon key cannot read or write). Optional: `OWNER_TELEGRAM_ID` (the monthly report is skipped without it), `TIMEZONE` (IANA name; defaults to the host's local tz, which on a serverless host means UTC).

Two more are required in production only, and both fail closed — if the variable is unset the endpoint answers 401 to everyone: `WEBHOOK_SECRET` (echoed by Telegram in `X-Telegram-Bot-Api-Secret-Token`, set via `setWebhook`) and `CRON_SECRET` (Vercel sends it as `Authorization: Bearer …`).

Because `config.py` validates at import, any `import handlers` / `import scheduler` needs the env set. For a throwaway check: `BOT_TOKEN=x SUPABASE_URL=https://x.supabase.co SUPABASE_KEY=x python -c "import handlers"`.

The `expenses` table must be created manually in Supabase from `schema.sql` — there are no migrations.

## Architecture

aiogram 3 bot, no ORM and no framework beyond aiogram/APScheduler/supabase-py.

**Two run modes share one set of handlers.** Production is serverless on Vercel: `api/telegram.py` receives a webhook and `api/cron.py` is hit by Vercel Cron. Local development uses `bot.py` (long polling + in-process APScheduler). Both import the same `router` and `format_report`, so business logic must never live in an entrypoint — put it in `handlers.py`, `db.py`, or `periods.py` or it will exist in only one mode.

The two modes are mutually exclusive at runtime: Telegram refuses `getUpdates` while a webhook is registered. To run locally, delete the webhook first (`deleteWebhook`), and re-register it afterwards.

- `app.py` — the ASGI entrypoint, a FastAPI app with both routes. `POST /api/telegram` verifies `WEBHOOK_SECRET` and feeds one `Update` to the dispatcher; `GET /api/cron` verifies `CRON_SECRET` and sends the report. Each request builds and closes its own `Bot` — there is no long-lived session on serverless.
- `pyproject.toml` — runtime dependencies **and** `[tool.vercel] entrypoint = "app:app"`. Vercel's Python runtime builds one ASGI app; the older "one file per function in `api/`" layout is not what this project uses, and adding `api/*.py` handler classes will break the build with "No python entrypoint found".
- `vercel.json` — cron schedule only.
- `reports.py` — `send_monthly_report(bot)`, shared by `app.py` and `scheduler.py` so the report exists in one place.
- `bot.py` — local entrypoint: `Bot`/`Dispatcher`, router, APScheduler, `start_polling`.
- `scheduler.py` — local-only: APScheduler `CronTrigger(day=1, hour=9)` in `TZINFO`, calling the same `send_monthly_report`.
- `config.py` — env parsing only, with deliberate import-time side effects (see above).
- `handlers.py` — all Telegram handlers, the `CATEGORIES` list, and `format_report`.
- `periods.py` — calendar-month window math. Pure functions, the only tested module.
- `db.py` — the only Supabase access point. Module-level `create_client`; every query is a sync supabase-py call wrapped in `asyncio.to_thread` so the event loop is never blocked.

**The webhook always answers 200**, even when the update raises — Telegram redelivers non-200 updates indefinitely, so a persistent bug would turn into an infinite loop. Failures are logged instead.

**Vercel Cron runs on UTC and ignores `TIMEZONE`.** The schedule in `vercel.json` is `0 4 1 * *` = 09:00 at UTC+5. `TIMEZONE` still matters inside the function, because it decides which calendar month `previous_month_range` picks. Changing the owner's timezone means editing both.

Dependencies live in `pyproject.toml`; `requirements-dev.txt` mirrors them plus pytest for a plain local venv. Keep the two in sync when adding a runtime dependency.

### Conventions that matter

**The bot is stateless by design.** A bare integer message renders a keyboard whose `callback_data` carries the amount (`cat:food:500`); the callback parses it with `CALLBACK_RE` and writes the row. Nothing is held between updates, so a redeploy mid-flow loses nothing. Do not reintroduce a module-level dict or FSM storage — that was removed deliberately, because a restart between "typed the amount" and "tapped the category" silently dropped the expense. Budget: `callback_data` is capped at 64 bytes; the longest current value is 19.

Double-submission is prevented by `edit_text` replacing the message (and its buttons) after a successful write — not by consuming state.

**Categories are stored as their display label, not their code.** `add_expense` is called with `CATEGORY_LABELS[code]` (e.g. `"🛒 Продукты"`), so the `category` column and the `summary` dict keys are emoji labels. `format_report` relies on this when it iterates `CATEGORIES` and checks `if label in summary` — which also means the report is ordered by `CATEGORIES`, not by amount. Renaming a label changes what new rows store and orphans existing rows in reports.

**Timestamps are naive UTC.** `schema.sql` uses `timestamp` (no tz). `db.py` converts to UTC and strips tzinfo before writing, and does the same to the range bounds when querying. Any new timestamp code must follow the same convert-then-strip pattern or comparisons will silently mismatch.

**Report windows are calendar months in `TZINFO`, computed in `periods.py`.** `/month` uses `current_month_range` (1st of this month → now); the scheduled report uses `previous_month_range` (the whole previous month). `get_summary` itself is window-agnostic — it takes arbitrary `start`/`end`, so don't bake period logic into it.

**Non-numeric text is ignored silently.** `@router.message(F.text)` returns early when the text doesn't match `^\d+$`; it is the catch-all handler, so any new text command must be registered before it via a more specific filter.

**Error handling is user-facing only.** Handlers catch broad `Exception` around DB calls and reply with a short message; nothing is logged beyond aiogram's own INFO logging. `_send_monthly_report` deliberately does *not* catch — a failure there should surface in the host's logs rather than vanish.

### Testing posture

`periods.py` is tested because month boundaries (year rollover, February, timezone) are where bugs actually hide. aiogram handlers are not tested — mocking the framework costs more than it catches for a bot this size. Follow that split: test pure logic, verify handlers by running the bot.

## Scope constraints (from TECH_SPEC.md and agreed with the owner)

The flow is fixed: send an amount, tap a category, done. Explicitly out of scope — free-text input like `500 кофе`, per-expense descriptions, fractional amounts, editing or deleting expenses, managing categories from the bot, multi-currency. `TECH_SPEC.md` lists "no overengineering" and "minimal dependencies" as requirements; keep changes small.
