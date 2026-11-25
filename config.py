"""Налаштування бота. Щоб адаптувати бота під іншого клієнта, змінюйте здебільшого цей файл."""
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(override=True)  # читає секрети з файлу .env (файл важливіший за змінні терміналу)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)  # Telegram ID власника, отримує сповіщення

TZ = ZoneInfo("Europe/Kyiv")

# --- Дані бізнесу (демо) ---
BUSINESS_NAME = "Barber Demo"
ADDRESS = "м. Хмельницький, вул. Прикладна, 1"
PHONE = "+380 00 000 00 00"
WORK_HOURS_TEXT = "Пн–Сб: 10:00–19:00, Нд — вихідний"

# Послуги: код -> (назва, ціна в грн). Ціни демонстраційні.
SERVICES = {
    "haircut": ("Чоловіча стрижка", 400),
    "beard": ("Оформлення бороди", 250),
    "combo": ("Стрижка + борода", 600),
    "kids": ("Дитяча стрижка", 300),
}

# --- Розклад ---
WORK_START_HOUR = 10   # перший слот
WORK_END_HOUR = 19     # кінець робочого дня (останній слот починається раніше)
SLOT_MINUTES = 60      # тривалість одного слоту
DAYS_AHEAD = 7         # на скільки днів уперед можна записатися
DAYS_OFF = {6}         # вихідні: 0 = понеділок ... 6 = неділя
MIN_LEAD_MINUTES = 30  # не можна записатися менше ніж за 30 хв до початку

REMIND_BEFORE_MINUTES = 120  # нагадування клієнту за 2 години
