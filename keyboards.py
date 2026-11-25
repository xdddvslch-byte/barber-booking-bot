"""Клавіатури (кнопки) бота."""
from datetime import date

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from timeslots import human_date

BTN_BOOK = "📅 Записатися"
BTN_MY = "📋 Мої записи"
BTN_PRICES = "💈 Послуги і ціни"
BTN_CONTACTS = "📍 Контакти"
BTN_CANCEL = "❌ Скасувати"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOOK)],
            [KeyboardButton(text=BTN_MY), KeyboardButton(text=BTN_PRICES)],
            [KeyboardButton(text=BTN_CONTACTS)],
        ],
        resize_keyboard=True,
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Надіслати мій номер", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def services_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, (title, price) in config.SERVICES.items():
        kb.button(text=f"{title} — {price} грн", callback_data=f"svc:{code}")
    kb.adjust(1)
    return kb.as_markup()


def dates_kb(dates: list[date]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in dates:
        kb.button(text=human_date(d), callback_data=f"date:{d.isoformat()}")
    kb.button(text="⬅️ Назад", callback_data="back:services")
    kb.adjust(3)
    return kb.as_markup()


def times_kb(times: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in times:
        kb.button(text=t, callback_data=f"time:{t}")
    kb.button(text="⬅️ Назад", callback_data="back:dates")
    kb.adjust(4)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Підтвердити", callback_data="confirm:yes")
    kb.button(text="❌ Скасувати", callback_data="confirm:no")
    kb.adjust(2)
    return kb.as_markup()


def my_bookings_kb(bookings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(
            text=f"❌ Скасувати {human_date(b['date'])} {b['time']}",
            callback_data=f"cancel:{b['id']}",
        )
    kb.adjust(1)
    return kb.as_markup()
