"""Робота з базою даних SQLite (файл bookings.db створюється автоматично)."""
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).with_name("bookings.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # доступ до полів за назвою: row["name"]
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                phone      TEXT    NOT NULL,
                service    TEXT    NOT NULL,
                date       TEXT    NOT NULL,   -- 2026-11-25
                time       TEXT    NOT NULL,   -- 10:00
                status     TEXT    NOT NULL DEFAULT 'active',  -- active / cancelled
                reminded   INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            -- Захист від подвійного запису: на один час може бути лише один активний запис
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_slot
                ON bookings(date, time) WHERE status = 'active';
            """
        )


def busy_times(date: str) -> set[str]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT time FROM bookings WHERE date = ? AND status = 'active'", (date,)
        ).fetchall()
    return {r["time"] for r in rows}


def create_booking(user_id: int, name: str, phone: str, service: str, date: str, time: str) -> int | None:
    """Повертає id запису або None, якщо цей час уже зайняли."""
    try:
        with closing(_connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO bookings (user_id, name, phone, service, date, time) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, phone, service, date, time),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def user_bookings(user_id: int, now: str) -> list[sqlite3.Row]:
    """Майбутні активні записи клієнта. now у форматі 'YYYY-MM-DD HH:MM'."""
    with closing(_connect()) as conn:
        return conn.execute(
            """SELECT * FROM bookings
               WHERE user_id = ? AND status = 'active' AND (date || ' ' || time) >= ?
               ORDER BY date, time""",
            (user_id, now),
        ).fetchall()


def cancel_booking(booking_id: int, user_id: int) -> sqlite3.Row | None:
    """Скасовує запис, лише якщо він належить цьому користувачу."""
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT * FROM bookings WHERE id = ? AND user_id = ? AND status = 'active'",
            (booking_id, user_id),
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
        return row


def bookings_between(date_from: str, date_to: str) -> list[sqlite3.Row]:
    """Активні записи з date_from по date_to включно (для адміністратора)."""
    with closing(_connect()) as conn:
        return conn.execute(
            """SELECT * FROM bookings
               WHERE status = 'active' AND date BETWEEN ? AND ?
               ORDER BY date, time""",
            (date_from, date_to),
        ).fetchall()


def due_reminders(now: str, until: str) -> list[sqlite3.Row]:
    """Записи, які починаються в проміжку (now, until] і ще не отримали нагадування."""
    with closing(_connect()) as conn:
        return conn.execute(
            """SELECT * FROM bookings
               WHERE status = 'active' AND reminded = 0
                 AND (date || ' ' || time) > ? AND (date || ' ' || time) <= ?""",
            (now, until),
        ).fetchall()


def mark_reminded(booking_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))
