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
# Транспорт — такси и общественный; Авто — своя машина (бензин, парковка, ремонт).
CATEGORIES = [
    ("food", "🛒 Продукты"),
    ("meals", "🍔 Питание"),
    ("transport", "🚕 Транспорт"),
    ("car", "🚗 Авто"),
    ("health", "💊 Здоровье"),
    ("shopping", "👕 Покупки"),
    ("marketplace", "🛍 Маркетплейсы"),
    ("subscriptions", "💻 Подписки"),
    ("gifts", "🎁 Подарки и тои"),
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
