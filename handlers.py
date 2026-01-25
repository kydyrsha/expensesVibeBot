import re
from datetime import datetime, timedelta, timezone
from typing import Dict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import add_expense, get_weekly_summary


router = Router()

AMOUNT_RE = re.compile(r"^\d+$")

CATEGORIES = [
    ("food", "🍔 Food"),
    ("transport", "🚕 Transport"),
    ("home", "🏠 Home"),
    ("entertainment", "🎮 Entertainment"),
    ("shopping", "🛒 Shopping"),
]
CATEGORY_LABELS = {code: label for code, label in CATEGORIES}

_pending_amounts: Dict[int, int] = {}


def _category_keyboard():
    builder = InlineKeyboardBuilder()
    for code, label in CATEGORIES:
        builder.button(text=label, callback_data=f"cat:{code}")
    builder.adjust(2)
    return builder.as_markup()


def format_weekly_report(summary: Dict[str, int], total: int) -> str:
    if not summary:
        return "No expenses this week."

    lines = ["Weekly summary:"]
    for _, label in CATEGORIES:
        if label in summary:
            lines.append(f"{label}: {summary[label]}")
    lines.append(f"Total: {total}")
    return "\n".join(lines)


@router.message(Command("start"))
async def start(message: Message) -> None:
    text = (
        "Welcome! Send a number to add an expense.\n"
        "I will ask you to choose a category.\n"
        "Use /week to see your weekly summary."
    )
    await message.answer(text)


@router.message(Command("week"))
async def week(message: Message) -> None:
    user_id = message.from_user.id
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)

    try:
        summary, total = await get_weekly_summary(user_id, start, end)
    except Exception:
        await message.answer("Failed to load weekly summary.")
        return

    await message.answer(format_weekly_report(summary, total))


@router.message(F.text)
async def add_amount(message: Message) -> None:
    text = (message.text or "").strip()
    if not AMOUNT_RE.fullmatch(text):
        return

    amount = int(text)
    if amount <= 0:
        await message.answer("Amount must be greater than 0.")
        return

    _pending_amounts[message.from_user.id] = amount
    await message.answer("Select a category:", reply_markup=_category_keyboard())


@router.callback_query(F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    pending_amount = _pending_amounts.pop(user_id, None)
    if pending_amount is None:
        await callback.answer("Send an amount first.", show_alert=True)
        return

    code = callback.data.split(":", 1)[1]
    label = CATEGORY_LABELS.get(code)
    if not label:
        await callback.answer("Unknown category.", show_alert=True)
        return

    try:
        await add_expense(user_id, pending_amount, label)
    except Exception:
        await callback.answer("Failed to save expense.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(f"Saved: {pending_amount} in {label}")
    await callback.answer()
