"""Перевірка й нормалізація українських мобільних номерів."""
import re

# Коди мобільних операторів України (оновлюйте, якщо з'являться нові):
# Vodafone: 50, 66, 75, 95, 99 · Київстар: 67, 68, 77, 96, 97, 98 · lifecell: 63, 73, 93
# 3Mob: 91 · PEOPLEnet: 92 · Інтертелеком: 94, 89
MOBILE_CODES = {
    "50", "66", "75", "95", "99",
    "67", "68", "77", "96", "97", "98",
    "63", "73", "93",
    "91", "92", "94", "89",
}

ALLOWED_CHARS = re.compile(r"^[\d\s\-()+]+$")  # цифри, пробіли, дефіси, дужки, плюс


def normalize_ua_phone(raw: str) -> str | None:
    """Повертає номер у форматі +380XXXXXXXXX або None, якщо номер неправильний.

    Приймає: +380671234567, 380671234567, 0671234567, 067 123 45 67, (067) 123-45-67.
    """
    if not raw or not ALLOWED_CHARS.match(raw.strip()):
        return None
    digits = re.sub(r"\D", "", raw)

    if len(digits) == 12 and digits.startswith("380"):
        national = digits[3:]          # 671234567
    elif len(digits) == 10 and digits.startswith("0"):
        national = digits[1:]          # 0671234567 -> 671234567
    else:
        return None

    if national[:2] not in MOBILE_CODES:
        return None
    return "+380" + national
