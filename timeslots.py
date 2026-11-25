"""Розрахунок доступних дат і вільного часу. Чисті функції, без Telegram."""
from datetime import date, datetime, timedelta

import config

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def all_slots() -> list[str]:
    """Усі слоти робочого дня: ['10:00', '11:00', ...]."""
    slots = []
    t = datetime(2000, 1, 1, config.WORK_START_HOUR)
    end = datetime(2000, 1, 1, config.WORK_END_HOUR)
    while t + timedelta(minutes=config.SLOT_MINUTES) <= end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=config.SLOT_MINUTES)
    return slots


def free_slots(day: date, busy: set[str], now: datetime) -> list[str]:
    """Вільні слоти на день з урахуванням зайнятих і того, що вже минуло."""
    earliest = now + timedelta(minutes=config.MIN_LEAD_MINUTES)
    result = []
    for slot in all_slots():
        if slot in busy:
            continue
        h, m = map(int, slot.split(":"))
        slot_dt = datetime(day.year, day.month, day.day, h, m, tzinfo=now.tzinfo)
        if slot_dt >= earliest:
            result.append(slot)
    return result


def available_dates(now: datetime) -> list[date]:
    """Робочі дні на DAYS_AHEAD днів уперед, починаючи з сьогодні."""
    today = now.date()
    days = (today + timedelta(days=i) for i in range(config.DAYS_AHEAD))
    return [d for d in days if d.weekday() not in config.DAYS_OFF]


def human_date(d: date | str) -> str:
    """2026-11-25 -> 'Ср 25.11'."""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{WEEKDAYS[d.weekday()]} {d.strftime('%d.%m')}"
