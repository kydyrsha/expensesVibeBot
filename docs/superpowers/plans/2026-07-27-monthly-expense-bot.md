# Месячный отчёт и деплой бота — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести бота с недельного отчёта на месячный, сделать его устойчивым к перезапускам и поднять на Railway так, чтобы отчёт приходил первого числа сам.

**Architecture:** Архитектура не меняется — один процесс с aiogram long polling плюс APScheduler, данные в Supabase Postgres. Состояние из памяти процесса убирается: сумма едет в `callback_data` кнопки, поэтому редеплой не ломает незавершённый ввод. Окно отчёта считается по календарным месяцам в таймзоне пользователя.

**Tech Stack:** Python 3.11, aiogram 3.x, APScheduler 3.x, supabase-py, Supabase Postgres, Railway.

---

## Порядок этапов

Этапы 1–4 — код, их можно делать и проверять локально. Этап 5 — инфраструктура Supabase, этап 6 — деплой. Этапы 5 и 6 требуют действий в веб-интерфейсе, которые агент выполнить не может: они расписаны как инструкции для человека.

---

### Task 1: Тесты на окна месяца

Самая хрупкая логика в этой задаче — границы месяцев (декабрь→январь, високосный год, таймзона). Только её и покрываем тестами; хендлеры aiogram тестировать не будем, это не окупается.

**Files:**
- Create: `periods.py`
- Create: `tests/test_periods.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Добавить pytest в зависимости**

В `requirements.txt` добавить строку (полное содержимое файла правится в Task 5, пока только дописываем):

```
pytest>=8,<9
```

- [ ] **Step 2: Написать падающий тест**

Создать `tests/test_periods.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from periods import current_month_range, previous_month_range

TZ = ZoneInfo("Europe/Moscow")


def test_previous_month_range_mid_year():
    now = datetime(2026, 7, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2026, 6, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)


def test_previous_month_range_crosses_year():
    now = datetime(2026, 1, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2025, 12, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2026, 1, 1, 0, 0, tzinfo=TZ)


def test_previous_month_range_after_february():
    now = datetime(2024, 3, 1, 9, 0, tzinfo=TZ)
    start, end = previous_month_range(now)
    assert start == datetime(2024, 2, 1, 0, 0, tzinfo=TZ)
    assert end == datetime(2024, 3, 1, 0, 0, tzinfo=TZ)


def test_current_month_range_ends_now():
    now = datetime(2026, 7, 15, 14, 30, tzinfo=TZ)
    start, end = current_month_range(now)
    assert start == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)
    assert end == now
```

- [ ] **Step 3: Убедиться, что тест падает**

Run: `python -m pytest tests/test_periods.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'periods'`

- [ ] **Step 4: Написать минимальную реализацию**

Создать `periods.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple


def current_month_range(now: datetime) -> Tuple[datetime, datetime]:
    """[первое число текущего месяца 00:00, now) в таймзоне now."""
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def previous_month_range(now: datetime) -> Tuple[datetime, datetime]:
    """[первое число прошлого месяца, первое число текущего) в таймзоне now."""
    end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (end - timedelta(days=1)).replace(day=1)
    return start, end
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `python -m pytest tests/test_periods.py -v`
Expected: PASS, 4 passed

- [ ] **Step 6: Коммит**

```bash
git add periods.py tests/test_periods.py requirements.txt
git commit -m "feat: add calendar month period helpers"
```

---

### Task 2: Переименовать выборку в БД

`get_weekly_summary` уже принимает произвольные `start`/`end` — недельного в ней осталось только имя. Переименовываем, чтобы имя не врало.

**Files:**
- Modify: `db.py:37`

- [ ] **Step 1: Переименовать функцию**

В `db.py` заменить сигнатуру:

```python
async def get_weekly_summary(
    user_id: int, start: datetime, end: datetime
) -> Tuple[Dict[str, int], int]:
```

на:

```python
async def get_summary(
    user_id: int, start: datetime, end: datetime
) -> Tuple[Dict[str, int], int]:
```

Тело функции не трогаем — конвертация в наивный UTC уже корректна и работает с любым окном.

- [ ] **Step 2: Проверить, что старое имя нигде не осталось**

Run: `grep -rn "get_weekly_summary" --include=*.py .`
Expected: четыре строки — импорт и вызов в `handlers.py`, импорт и вызов в `scheduler.py`. Они чинятся в Task 3 и Task 4.

- [ ] **Step 3: Коммит**

```bash
git add db.py
git commit -m "refactor: rename get_weekly_summary to get_summary"
```

---

### Task 3: Stateless-ввод и команда /month

Убираем `_pending_amounts`: сумма едет в `callback_data`. Это то, из-за чего бот переживает редеплой.

**Files:**
- Modify: `handlers.py`

- [ ] **Step 1: Заменить содержимое handlers.py**

Полное новое содержимое `handlers.py` (категории и комментарий сохраняются как есть):

```python
import re
from datetime import datetime
from typing import Dict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TZINFO
from db import add_expense, get_summary
from periods import current_month_range


router = Router()

AMOUNT_RE = re.compile(r"^\d+$")
CALLBACK_RE = re.compile(r"^cat:(?P<code>[a-z]+):(?P<amount>\d+)$")

# Продукты — магазины у дома и супермаркеты; Питание — еда вне дома.
# Покупки — всё офлайн, Маркетплейсы — то же самое онлайн (Ozon, WB, Temu).
CATEGORIES = [
    ("food", "🛒 Продукты"),
    ("meals", "🍔 Питание"),
    ("transport", "🚕 Транспорт"),
    ("home", "🏠 Жильё"),
    ("health", "💊 Здоровье"),
    ("shopping", "👕 Покупки"),
    ("marketplace", "🛍 Маркетплейсы"),
    ("fun", "🎮 Развлечения"),
    ("other", "📦 Прочее"),
]
CATEGORY_LABELS = {code: label for code, label in CATEGORIES}


def _category_keyboard(amount: int):
    builder = InlineKeyboardBuilder()
    for code, label in CATEGORIES:
        builder.button(text=label, callback_data=f"cat:{code}:{amount}")
    builder.adjust(2)
    return builder.as_markup()


def format_report(title: str, summary: Dict[str, int], total: int) -> str:
    if not summary:
        return f"{title}: трат нет."

    lines = [f"{title}:"]
    for _, label in CATEGORIES:
        if label in summary:
            lines.append(f"{label}: {summary[label]}")
    lines.append(f"Итого: {total}")
    return "\n".join(lines)


@router.message(Command("start"))
async def start(message: Message) -> None:
    text = (
        "Привет! Пришли число — это сумма траты.\n"
        "Дальше выбери категорию кнопкой.\n"
        "Команда /month покажет траты за текущий месяц.\n"
        "Первого числа каждого месяца пришлю отчёт за прошлый месяц."
    )
    await message.answer(text)


@router.message(Command("month"))
async def month(message: Message) -> None:
    start_at, end_at = current_month_range(datetime.now(TZINFO))

    try:
        summary, total = await get_summary(message.from_user.id, start_at, end_at)
    except Exception:
        await message.answer("Не удалось загрузить отчёт.")
        return

    await message.answer(format_report("Траты за текущий месяц", summary, total))


@router.message(F.text)
async def add_amount(message: Message) -> None:
    text = (message.text or "").strip()
    if not AMOUNT_RE.fullmatch(text):
        return

    amount = int(text)
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    await message.answer("Выбери категорию:", reply_markup=_category_keyboard(amount))


@router.callback_query(F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery) -> None:
    match = CALLBACK_RE.fullmatch(callback.data or "")
    if not match:
        await callback.answer("Не понял кнопку.", show_alert=True)
        return

    label = CATEGORY_LABELS.get(match.group("code"))
    if not label:
        await callback.answer("Неизвестная категория.", show_alert=True)
        return

    amount = int(match.group("amount"))

    try:
        await add_expense(callback.from_user.id, amount, label)
    except Exception:
        await callback.answer("Не удалось сохранить трату.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(f"Записал: {amount} — {label}")
    await callback.answer()
```

- [ ] **Step 2: Проверить синтаксис**

Run: `python -m py_compile handlers.py`
Expected: без вывода, код возврата 0

- [ ] **Step 3: Проверить, что состояние в памяти исчезло**

Run: `grep -n "_pending_amounts" handlers.py`
Expected: ничего не найдено (grep вернёт код 1)

- [ ] **Step 4: Коммит**

```bash
git add handlers.py
git commit -m "feat: stateless amount in callback_data, /month command, ru texts"
```

---

### Task 4: Отчёт первого числа месяца

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: Заменить содержимое scheduler.py**

```python
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
```

- [ ] **Step 2: Проверить, что всё импортируется вместе**

Run:

```bash
BOT_TOKEN=x SUPABASE_URL=https://x.supabase.co SUPABASE_KEY=x TIMEZONE=Europe/Moscow python -c "import bot, scheduler, handlers, periods; print('imports ok')"
```

Expected: `imports ok`

- [ ] **Step 3: Проверить, что старое имя функции нигде не осталось**

Run: `grep -rn "get_weekly_summary\|format_weekly_report" --include=*.py .`
Expected: ничего не найдено

- [ ] **Step 4: Коммит**

```bash
git add scheduler.py
git commit -m "feat: monthly report on the 1st instead of weekly"
```

---

### Task 5: Подготовка репозитория к деплою

**Files:**
- Create: `.gitignore`
- Create: `Procfile`
- Modify: `requirements.txt`
- Modify: `schema.sql`

- [ ] **Step 1: Создать .gitignore**

```
__pycache__/
*.pyc
.venv/
.env
.pytest_cache/
```

- [ ] **Step 2: Зафиксировать версии зависимостей**

Полное содержимое `requirements.txt`:

```
aiogram>=3,<4
APScheduler>=3.10,<4
supabase>=2,<3
pytest>=8,<9
```

Верхние границы важны: код написан под aiogram 3.x, у 2.x и предполагаемой 4.x другой API.

- [ ] **Step 3: Создать Procfile**

Railway должен понимать, что это фоновый процесс, а не веб-сервер — иначе будет ждать открытый порт и считать деплой упавшим:

```
worker: python bot.py
```

- [ ] **Step 4: Добавить RLS в schema.sql**

Дописать в конец `schema.sql`:

```sql
alter table expenses enable row level security;
```

Без политик это полностью закрывает таблицу для anon-ключа. Бот должен ходить с service_role-ключом, который RLS обходит (см. Task 6).

- [ ] **Step 5: Прогнать тесты и проверить, что дерево чистое**

Run: `python -m pytest -q && git status --short`
Expected: тесты проходят; в `git status` нет `__pycache__` и `.venv`

- [ ] **Step 6: Коммит**

```bash
git add .gitignore Procfile requirements.txt schema.sql
git commit -m "chore: pin deps, add Procfile, gitignore and RLS"
```

---

### Task 6: Supabase — создать проект и таблицу

Делается руками в веб-интерфейсе, агент это выполнить не может.

- [ ] **Step 1:** Зайти на https://supabase.com/dashboard, создать новый проект. Регион выбрать поближе, пароль БД сохранить в менеджер паролей.
- [ ] **Step 2:** Открыть SQL Editor, вставить содержимое `schema.sql` целиком и выполнить.
- [ ] **Step 3:** Проверить в Table Editor, что таблица `expenses` появилась и рядом с ней стоит отметка RLS enabled.
- [ ] **Step 4:** Settings → API. Скопировать **Project URL** и ключ **service_role** (не anon — anon упрётся в RLS). Ключ секретный, в git не класть.

---

### Task 7: Деплой на Railway

- [ ] **Step 1:** Запушить ветку на GitHub (`gh auth status` уже настроен, аккаунт kydyrsha).
- [ ] **Step 2:** На https://railway.app создать проект из этого GitHub-репозитория.
- [ ] **Step 3:** В разделе Variables задать четыре переменные: `BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY` (service_role), `OWNER_TELEGRAM_ID`, и пятую `TIMEZONE` — например `Europe/Moscow`. Без `TIMEZONE` бот возьмёт таймзону контейнера, то есть UTC, и отчёт придёт не в 9:00 по-твоему.
- [ ] **Step 4:** Дождаться деплоя, открыть логи. Ожидаемо: строка уровня INFO от aiogram про старт polling и отсутствие трейсбеков.
- [ ] **Step 5:** Написать боту `/start`, затем число, выбрать категорию. Ожидаемо: сообщение заменяется на «Записал: N — категория».
- [ ] **Step 6:** Открыть Table Editor в Supabase и убедиться, что строка появилась.
- [ ] **Step 7:** Отправить `/month` — трата должна быть в отчёте.

---

## Как проверить месячный отчёт, не дожидаясь первого числа

Ждать до 1-го числа, чтобы узнать, что отчёт не работает, — плохая идея. Разовая проверка логики:

```bash
BOT_TOKEN=$BOT_TOKEN SUPABASE_URL=$SUPABASE_URL SUPABASE_KEY=$SUPABASE_KEY \
OWNER_TELEGRAM_ID=$OWNER_TELEGRAM_ID TIMEZONE=Europe/Moscow \
python -c "
import asyncio
from aiogram import Bot
from config import BOT_TOKEN
from scheduler import _send_monthly_report

async def main():
    bot = Bot(token=BOT_TOKEN)
    await _send_monthly_report(bot)
    await bot.session.close()

asyncio.run(main())
"
```

Придёт отчёт за прошлый месяц. Если трат за прошлый месяц нет, ответ будет «трат нет» — это тоже валидный результат, значит цепочка работает.

---

## Что осознанно не делаем

Зафиксировано в обсуждении, чтобы не всплыло как «забыли»:

- Ввод одним сообщением («500 кофе») — нет, ввод остаётся двухшаговым.
- Описание траты в БД и отчёте — нет.
- Дробные суммы — нет, только целые.
- Редактирование и удаление трат, управление категориями из бота — исключено в `TECH_SPEC.md`.
- Мультивалютность — нет.
