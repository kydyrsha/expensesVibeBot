# Telegram Expense Bot (Personal)

Simple personal expense-tracking bot built with aiogram and Supabase.

## Features
- Add an expense by sending a number
- Select a category via inline buttons
- `/week` shows a weekly summary by category
- Automatic weekly report on Sundays at 20:00 (local time)

## Requirements
- Python 3.11
- Supabase project (PostgreSQL)

## Setup

1) Create the `expenses` table in Supabase:

```sql
-- see schema.sql
```

2) Set environment variables:

```bash
export BOT_TOKEN="your_telegram_bot_token"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your_supabase_key"
export OWNER_TELEGRAM_ID="your_telegram_user_id"
# Optional:
export TIMEZONE="Europe/Berlin"
```

3) Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4) Run the bot:

```bash
python bot.py
```

## Notes
- Amounts are stored as integers.
- The weekly report uses the last 7 days of data.
