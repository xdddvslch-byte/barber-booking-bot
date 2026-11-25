"""Telegram-бот запису на послуги (демо для барбершопу).

Запуск:  python bot.py
"""
import asyncio
import html
import logging
import re
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
import db
import keyboards as kb
from phone import normalize_ua_phone
from timeslots import available_dates, free_slots, human_date

router = Router()


class Booking(StatesGroup):
    """Кроки запису. Бот пам'ятає, на якому кроці зараз клієнт."""
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


def now() -> datetime:
    return datetime.now(config.TZ)


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M")


def service_title(code: str) -> str:
    title, price = config.SERVICES.get(code, (code, 0))
    return f"{title} ({price} грн)"


def booking_text(b) -> str:
    return (
        f"💈 {service_title(b['service'])}\n"
        f"📅 {human_date(b['date'])} о {b['time']}\n"
        f"👤 {html.escape(b['name'])}, {html.escape(b['phone'])}"
    )


async def notify_admin(bot: Bot, text: str) -> None:
    if not config.ADMIN_ID:
        return
    try:
        await bot.send_message(config.ADMIN_ID, text)
    except Exception as e:  # адмін міг не натиснути /start у боті
        logging.warning("Не вдалося надіслати повідомлення адміну: %s", e)


# ---------- Головне меню ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Вітаємо в <b>{config.BUSINESS_NAME}</b>! 👋\n"
        "Тут можна записатися на послугу за хвилину.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == kb.BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Запис скасовано. Повертаю в меню.", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_PRICES)
async def show_prices(message: Message, state: FSMContext):
    await state.clear()
    lines = [f"• {title} — <b>{price} грн</b>" for title, price in config.SERVICES.values()]
    await message.answer("💈 <b>Послуги і ціни</b>\n\n" + "\n".join(lines))


@router.message(F.text == kb.BTN_CONTACTS)
async def show_contacts(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"📍 {config.ADDRESS}\n📞 {config.PHONE}\n🕙 {config.WORK_HOURS_TEXT}"
    )


@router.message(F.text == kb.BTN_MY)
async def show_my_bookings(message: Message, state: FSMContext):
    await state.clear()
    bookings = db.user_bookings(message.from_user.id, now_str())
    if not bookings:
        await message.answer("У вас немає активних записів.")
        return
    text = "📋 <b>Ваші записи:</b>\n\n" + "\n\n".join(booking_text(b) for b in bookings)
    await message.answer(text, reply_markup=kb.my_bookings_kb(bookings))


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking(call: CallbackQuery, bot: Bot):
    booking_id = int(call.data.split(":", 1)[1])
    row = db.cancel_booking(booking_id, call.from_user.id)
    if row is None:
        await call.answer("Запис уже скасовано або не знайдено.", show_alert=True)
        return
    await call.message.edit_text("Запис скасовано ✅\n\n" + booking_text(row))
    await call.answer()
    await notify_admin(bot, "❌ <b>Клієнт скасував запис</b>\n\n" + booking_text(row))


# ---------- Запис: крок за кроком ----------

@router.message(F.text == kb.BTN_BOOK)
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Booking.service)
    await message.answer("Оберіть послугу:", reply_markup=kb.services_kb())


@router.callback_query(Booking.service, F.data.startswith("svc:"))
async def choose_service(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":", 1)[1]
    if code not in config.SERVICES:
        await call.answer("Невідома послуга", show_alert=True)
        return
    await state.update_data(service=code)
    await state.set_state(Booking.date)
    await call.message.edit_text(
        f"Послуга: <b>{service_title(code)}</b>\nОберіть дату:",
        reply_markup=kb.dates_kb(available_dates(now())),
    )
    await call.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    day_str = call.data.split(":", 1)[1]
    day = date.fromisoformat(day_str)
    times = free_slots(day, db.busy_times(day_str), now())
    if not times:
        await call.answer("На цей день вільного часу немає 😔", show_alert=True)
        return
    await state.update_data(date=day_str)
    await state.set_state(Booking.time)
    await call.message.edit_text(
        f"📅 {human_date(day)}\nОберіть час:", reply_markup=kb.times_kb(times)
    )
    await call.answer()


@router.callback_query(F.data == "back:services")
async def back_to_services(call: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.service)
    await call.message.edit_text("Оберіть послугу:", reply_markup=kb.services_kb())
    await call.answer()


@router.callback_query(F.data == "back:dates")
async def back_to_dates(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "service" not in data:  # стан втрачено (наприклад, бот перезапускали)
        await back_to_services(call, state)
        return
    await state.set_state(Booking.date)
    await call.message.edit_text(
        f"Послуга: <b>{service_title(data['service'])}</b>\nОберіть дату:",
        reply_markup=kb.dates_kb(available_dates(now())),
    )
    await call.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def choose_time(call: CallbackQuery, state: FSMContext):
    time_str = call.data.split(":", 1)[1]
    data = await state.get_data()
    day = date.fromisoformat(data["date"])
    if time_str not in free_slots(day, db.busy_times(data["date"]), now()):
        await call.answer("Цей час щойно зайняли, оберіть інший.", show_alert=True)
        return
    await state.update_data(time=time_str)
    await state.set_state(Booking.name)
    await call.message.edit_text(
        f"💈 {service_title(data['service'])}\n📅 {human_date(day)} о {time_str}"
    )
    await call.message.answer("Як до вас звертатися? Напишіть ім'я:")
    await call.answer()


@router.message(Booking.name, F.text)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not 2 <= len(name) <= 50:
        await message.answer("Ім'я має містити від 2 до 50 символів. Спробуйте ще раз:")
        return
    await state.update_data(name=name)
    await state.set_state(Booking.phone)
    await message.answer(
        "Надішліть номер телефону кнопкою нижче або напишіть його (наприклад, +380671234567):",
        reply_markup=kb.phone_kb(),
    )


@router.message(Booking.phone, F.contact | F.text)
async def enter_phone(message: Message, state: FSMContext):
    if message.contact:
        # Кнопка «Надіслати мій номер»: Telegram гарантує, що номер належить користувачу.
        # Але через скрепку можна надіслати чужий контакт, тому перевіряємо, чий він.
        if message.contact.user_id != message.from_user.id:
            await message.answer("Це чужий контакт. Натисніть кнопку «📱 Надіслати мій номер» або введіть свій номер.")
            return
        digits = re.sub(r"\D", "", message.contact.phone_number)
        phone = "+" + digits
        verified = True
    else:
        phone = normalize_ua_phone(message.text)
        verified = False
        if phone is None:
            await message.answer(
                "Не схоже на український мобільний номер.\n"
                "Приклади: +380671234567 або 0671234567.\n"
                "Найпростіше — натиснути кнопку «📱 Надіслати мій номер»."
            )
            return
    await state.update_data(phone=phone, phone_verified=verified)
    await state.set_state(Booking.confirm)
    data = await state.get_data()
    await message.answer("Номер отримано ✅", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "Перевірте дані:\n\n" + booking_text(data), reply_markup=kb.confirm_kb()
    )


@router.callback_query(Booking.confirm, F.data == "confirm:no")
async def confirm_no(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Запис скасовано.")
    await call.message.answer("Повертаю в меню.", reply_markup=kb.main_menu())
    await call.answer()


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def confirm_yes(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    booking_id = db.create_booking(
        call.from_user.id, data["name"], data["phone"], data["service"], data["date"], data["time"]
    )
    if booking_id is None:
        await state.set_state(Booking.date)
        await call.message.edit_text(
            "На жаль, цей час щойно зайняли. Оберіть іншу дату або час:",
            reply_markup=kb.dates_kb(available_dates(now())),
        )
        await call.answer()
        return
    await state.clear()
    await call.message.edit_text("✅ <b>Ви записані!</b>\n\n" + booking_text(data))
    await call.message.answer(
        f"Нагадаємо за {config.REMIND_BEFORE_MINUTES // 60} год до візиту. "
        "Скасувати можна в розділі «Мої записи».",
        reply_markup=kb.main_menu(),
    )
    await call.answer()
    username = f" (@{call.from_user.username})" if call.from_user.username else ""
    phone_note = "✅ номер підтверджено Telegram" if data.get("phone_verified") else "✍️ номер введено вручну"
    await notify_admin(
        bot,
        f"🆕 <b>Новий запис #{booking_id}</b>{username}\n\n" + booking_text(data) + f"\n{phone_note}",
    )


# Клієнт натиснув стару кнопку після перезапуску бота або поза потрібним кроком
@router.callback_query(F.data.startswith(("svc:", "date:", "time:", "confirm:")))
async def stale_button(call: CallbackQuery):
    await call.answer("Ця кнопка вже неактуальна. Натисніть «📅 Записатися» ще раз.", show_alert=True)


# ---------- Команди адміністратора ----------

def is_admin(message: Message) -> bool:
    return message.from_user.id == config.ADMIN_ID


def admin_list(title: str, bookings) -> str:
    if not bookings:
        return f"{title}\n\nЗаписів немає."
    return f"{title}\n\n" + "\n\n".join(f"#{b['id']}\n" + booking_text(b) for b in bookings)


@router.message(Command("today"))
async def admin_today(message: Message):
    if not is_admin(message):
        return
    d = now().date().isoformat()
    await message.answer(admin_list("📅 <b>Записи на сьогодні</b>", db.bookings_between(d, d)))


@router.message(Command("week"))
async def admin_week(message: Message):
    if not is_admin(message):
        return
    d1 = now().date()
    d2 = d1 + timedelta(days=6)
    await message.answer(
        admin_list("🗓 <b>Записи на 7 днів</b>", db.bookings_between(d1.isoformat(), d2.isoformat()))
    )


@router.message(Command("admin"))
async def admin_help(message: Message):
    if not is_admin(message):
        return
    await message.answer("Команди адміністратора:\n/today — записи на сьогодні\n/week — на 7 днів")


@router.message(StateFilter(Booking.service, Booking.date, Booking.time, Booking.confirm))
async def use_buttons_hint(message: Message):
    await message.answer("Оберіть варіант кнопками в повідомленні вище 👆 або натисніть /cancel")


@router.message(StateFilter(None))
async def fallback(message: Message):
    await message.answer("Скористайтеся кнопками меню 👇", reply_markup=kb.main_menu())


# ---------- Автоматичні нагадування ----------

async def reminder_loop(bot: Bot) -> None:
    """Раз на хвилину перевіряє, кому пора надіслати нагадування."""
    while True:
        try:
            start = now()
            until = start + timedelta(minutes=config.REMIND_BEFORE_MINUTES)
            for b in db.due_reminders(start.strftime("%Y-%m-%d %H:%M"), until.strftime("%Y-%m-%d %H:%M")):
                try:
                    await bot.send_message(
                        b["user_id"],
                        "⏰ <b>Нагадування про візит</b>\n\n" + booking_text(b)
                        + f"\n\n📍 {config.ADDRESS}",
                    )
                except Exception as e:  # клієнт міг заблокувати бота
                    logging.warning("Нагадування #%s не надіслано: %s", b["id"], e)
                db.mark_reminded(b["id"])
        except Exception:
            logging.exception("Помилка в циклі нагадувань")
        await asyncio.sleep(60)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("Не знайдено BOT_TOKEN. Створіть файл .env (див. README.md).")
    db.init_db()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    reminder_task = asyncio.create_task(reminder_loop(bot))  # noqa: F841 (тримаємо посилання)
    logging.info("Бот запущено. Зупинити: Ctrl+C")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
