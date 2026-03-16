import sqlite3
import threading
from datetime import datetime


class Database:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._lock = threading.RLock()

    def close(self) -> None:
        self._conn.close()

    def init(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            # Partial unique indexes enforce one active booking per user and per slot.
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS working_days (
                    work_date TEXT PRIMARY KEY,
                    is_closed INTEGER NOT NULL DEFAULT 0 CHECK (is_closed IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS time_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_date TEXT NOT NULL,
                    slot_time TEXT NOT NULL,
                    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1)),
                    FOREIGN KEY(work_date) REFERENCES working_days(work_date) ON DELETE CASCADE,
                    UNIQUE(work_date, slot_time)
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    slot_id INTEGER NOT NULL,
                    service_category TEXT NOT NULL DEFAULT '',
                    service_name TEXT NOT NULL DEFAULT '',
                    service_price INTEGER NOT NULL DEFAULT 0,
                    nail_length TEXT NOT NULL DEFAULT '',
                    nail_shape TEXT NOT NULL DEFAULT '',
                    coating_type TEXT NOT NULL DEFAULT '',
                    client_comment TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    reminder_at TEXT,
                    cancelled_at TEXT,
                    FOREIGN KEY(slot_id) REFERENCES time_slots(id) ON DELETE CASCADE
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_one_active_per_user
                ON bookings(user_id) WHERE status = 'active';

                CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_one_active_per_slot
                ON bookings(slot_id) WHERE status = 'active';
                """
            )
            self._ensure_booking_columns()
            self._conn.commit()

    def _ensure_booking_columns(self) -> None:
        """Apply lightweight schema migrations for existing DB files."""
        existing_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(bookings)").fetchall()
        }
        required_columns = {
            "service_category": "TEXT NOT NULL DEFAULT ''",
            "service_name": "TEXT NOT NULL DEFAULT ''",
            "service_price": "INTEGER NOT NULL DEFAULT 0",
            "nail_length": "TEXT NOT NULL DEFAULT ''",
            "nail_shape": "TEXT NOT NULL DEFAULT ''",
            "coating_type": "TEXT NOT NULL DEFAULT ''",
            "client_comment": "TEXT NOT NULL DEFAULT ''",
        }
        for col_name, col_def in required_columns.items():
            if col_name not in existing_cols:
                self._conn.execute(
                    f"ALTER TABLE bookings ADD COLUMN {col_name} {col_def}"
                )

    def _rows_to_dict(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    def add_working_day(self, work_date: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO working_days(work_date, is_closed)
                VALUES(?, 0)
                ON CONFLICT(work_date) DO UPDATE SET is_closed = 0
                """,
                (work_date,),
            )
            self._conn.commit()

    def close_day(self, work_date: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO working_days(work_date, is_closed)
                VALUES(?, 1)
                ON CONFLICT(work_date) DO UPDATE SET is_closed = 1
                """,
                (work_date,),
            )
            self._conn.execute(
                "UPDATE time_slots SET is_available = 0 WHERE work_date = ?",
                (work_date,),
            )
            self._conn.commit()

    def add_slot(self, work_date: str, slot_time: str) -> bool:
        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO working_days(work_date, is_closed)
                    VALUES(?, 0)
                    ON CONFLICT(work_date) DO NOTHING
                    """,
                    (work_date,),
                )
                self._conn.execute(
                    """
                    INSERT INTO time_slots(work_date, slot_time, is_available)
                    VALUES(?, ?, 1)
                    """,
                    (work_date, slot_time),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                self._conn.rollback()
                return False

    def ensure_min_available_slots(
        self,
        date_from: str,
        date_to: str,
        min_slots_per_day: int = 3,
    ) -> None:
        """Ensure each date in range has at least N available slots."""
        start = datetime.strptime(date_from, "%Y-%m-%d").date()
        end = datetime.strptime(date_to, "%Y-%m-%d").date()
        candidate_times = [
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
            "20:00",
        ]

        current = start
        while current <= end:
            work_date = current.isoformat()
            self.add_working_day(work_date)

            with self._lock:
                cur = self._conn.execute(
                    """
                    SELECT slot_time, is_available
                    FROM time_slots
                    WHERE work_date = ?
                    """,
                    (work_date,),
                )
                rows = cur.fetchall()

            existing_times = {row["slot_time"] for row in rows}
            available_count = sum(1 for row in rows if row["is_available"] == 1)

            if available_count < min_slots_per_day:
                for slot_time in candidate_times:
                    if slot_time in existing_times:
                        continue
                    if self.add_slot(work_date, slot_time):
                        available_count += 1
                        existing_times.add(slot_time)
                    if available_count >= min_slots_per_day:
                        break

            current = current.fromordinal(current.toordinal() + 1)

    def delete_slot(self, slot_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT b.id
                FROM bookings b
                WHERE b.slot_id = ? AND b.status = 'active'
                """,
                (slot_id,),
            )
            active_booking = cur.fetchone()
            if active_booking:
                return False

            self._conn.execute("DELETE FROM time_slots WHERE id = ?", (slot_id,))
            self._conn.commit()
            return True

    def get_available_dates(self, date_from: str, date_to: str) -> set[str]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT DISTINCT ts.work_date
                FROM time_slots ts
                JOIN working_days wd ON wd.work_date = ts.work_date
                WHERE ts.is_available = 1
                  AND wd.is_closed = 0
                  AND ts.work_date BETWEEN ? AND ?
                ORDER BY ts.work_date
                """,
                (date_from, date_to),
            )
            return {row["work_date"] for row in cur.fetchall()}

    def get_available_slots(self, work_date: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT ts.id, ts.slot_time
                FROM time_slots ts
                JOIN working_days wd ON wd.work_date = ts.work_date
                WHERE ts.work_date = ?
                  AND ts.is_available = 1
                  AND wd.is_closed = 0
                ORDER BY ts.slot_time
                """,
                (work_date,),
            )
            return self._rows_to_dict(cur.fetchall())

    def get_slots_by_date(self, work_date: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT id, slot_time, is_available
                FROM time_slots
                WHERE work_date = ?
                ORDER BY slot_time
                """,
                (work_date,),
            )
            return self._rows_to_dict(cur.fetchall())

    def get_slot_with_date(self, slot_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT ts.id, ts.work_date, ts.slot_time, ts.is_available, wd.is_closed
                FROM time_slots ts
                JOIN working_days wd ON wd.work_date = ts.work_date
                WHERE ts.id = ?
                """,
                (slot_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_booking_by_user(self, user_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT b.id, b.user_id, b.full_name, b.phone, b.slot_id, b.reminder_at,
                       b.service_category, b.service_name, b.service_price,
                       b.nail_length, b.nail_shape, b.coating_type, b.client_comment,
                       ts.work_date, ts.slot_time
                FROM bookings b
                JOIN time_slots ts ON ts.id = b.slot_id
                WHERE b.user_id = ? AND b.status = 'active'
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_booking(
        self,
        user_id: int,
        full_name: str,
        phone: str,
        slot_id: int,
        created_at: str,
        reminder_at: str | None,
        service_category: str,
        service_name: str,
        service_price: int,
        nail_length: str,
        nail_shape: str,
        coating_type: str,
        client_comment: str,
    ) -> dict | None:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute("BEGIN IMMEDIATE")
                cur.execute(
                    """
                    SELECT ts.id, ts.work_date, ts.slot_time, ts.is_available, wd.is_closed
                    FROM time_slots ts
                    JOIN working_days wd ON wd.work_date = ts.work_date
                    WHERE ts.id = ?
                    """,
                    (slot_id,),
                )
                slot = cur.fetchone()
                if not slot or slot["is_available"] == 0 or slot["is_closed"] == 1:
                    cur.execute("ROLLBACK")
                    return None

                cur.execute(
                    """
                    SELECT 1
                    FROM bookings
                    WHERE user_id = ? AND status = 'active'
                    LIMIT 1
                    """,
                    (user_id,),
                )
                already_booked = cur.fetchone()
                if already_booked:
                    cur.execute("ROLLBACK")
                    return None

                cur.execute(
                    "UPDATE time_slots SET is_available = 0 WHERE id = ?",
                    (slot_id,),
                )
                cur.execute(
                    """
                    INSERT INTO bookings(
                        user_id, full_name, phone, slot_id,
                        service_category, service_name, service_price,
                        nail_length, nail_shape, coating_type, client_comment,
                        status, created_at, reminder_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        user_id,
                        full_name,
                        phone,
                        slot_id,
                        service_category,
                        service_name,
                        service_price,
                        nail_length,
                        nail_shape,
                        coating_type,
                        client_comment,
                        created_at,
                        reminder_at,
                    ),
                )
                booking_id = cur.lastrowid
                self._conn.commit()
                return self.get_booking_by_id(booking_id)
            except sqlite3.Error:
                self._conn.rollback()
                return None

    def cancel_booking_by_id(self, booking_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                """
                SELECT id, user_id, slot_id
                FROM bookings
                WHERE id = ? AND status = 'active'
                """,
                (booking_id,),
            )
            booking = cur.fetchone()
            if not booking:
                cur.execute("ROLLBACK")
                return None

            cancelled_at = datetime.now().isoformat()
            cur.execute(
                """
                UPDATE bookings
                SET status = 'cancelled', cancelled_at = ?
                WHERE id = ?
                """,
                (cancelled_at, booking_id),
            )
            cur.execute(
                """
                UPDATE time_slots
                SET is_available = 1
                WHERE id = ?
                """,
                (booking["slot_id"],),
            )
            self._conn.commit()
            return {"id": booking["id"], "user_id": booking["user_id"]}

    def cancel_booking_by_user(self, user_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT id
                FROM bookings
                WHERE user_id = ? AND status = 'active'
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self.cancel_booking_by_id(row["id"])

    def get_booking_by_id(self, booking_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT b.id, b.user_id, b.full_name, b.phone, b.slot_id,
                       b.service_category, b.service_name, b.service_price,
                       b.nail_length, b.nail_shape, b.coating_type, b.client_comment,
                       b.status, b.created_at, b.reminder_at,
                       ts.work_date, ts.slot_time
                FROM bookings b
                JOIN time_slots ts ON ts.id = b.slot_id
                WHERE b.id = ?
                """,
                (booking_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_bookings_by_date(self, work_date: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT b.id, b.user_id, b.full_name, b.phone, b.service_name, ts.slot_time
                FROM bookings b
                JOIN time_slots ts ON ts.id = b.slot_id
                WHERE ts.work_date = ? AND b.status = 'active'
                ORDER BY ts.slot_time
                """,
                (work_date,),
            )
            return self._rows_to_dict(cur.fetchall())

    def get_active_bookings_by_date(self, work_date: str) -> list[dict]:
        return self.get_bookings_by_date(work_date)

    def get_day_schedule(self, work_date: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT ts.id AS slot_id, ts.slot_time, ts.is_available,
                       b.id AS booking_id, b.full_name, b.phone
                FROM time_slots ts
                LEFT JOIN bookings b ON b.slot_id = ts.id AND b.status = 'active'
                WHERE ts.work_date = ?
                ORDER BY ts.slot_time
                """,
                (work_date,),
            )
            return self._rows_to_dict(cur.fetchall())

    def get_dates_with_slots(self, date_from: str, date_to: str) -> set[str]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT DISTINCT work_date
                FROM time_slots
                WHERE work_date BETWEEN ? AND ?
                ORDER BY work_date
                """,
                (date_from, date_to),
            )
            return {row["work_date"] for row in cur.fetchall()}

    def get_dates_with_bookings(self, date_from: str, date_to: str) -> set[str]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT DISTINCT ts.work_date
                FROM bookings b
                JOIN time_slots ts ON ts.id = b.slot_id
                WHERE b.status = 'active' AND ts.work_date BETWEEN ? AND ?
                ORDER BY ts.work_date
                """,
                (date_from, date_to),
            )
            return {row["work_date"] for row in cur.fetchall()}

    def get_bookings_for_reminders(self, now_iso: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT b.id, b.user_id, b.reminder_at, ts.slot_time, ts.work_date
                FROM bookings b
                JOIN time_slots ts ON ts.id = b.slot_id
                WHERE b.status = 'active'
                  AND b.reminder_at IS NOT NULL
                  AND b.reminder_at > ?
                """,
                (now_iso,),
            )
            return self._rows_to_dict(cur.fetchall())
