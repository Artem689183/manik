from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.db import Database


class ReminderScheduler:
    def __init__(self, bot: Bot, db: Database, timezone: str) -> None:
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler(timezone=timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_booking(self, booking_id: int, reminder_at: str | None) -> None:
        if not reminder_at:
            return
        run_dt = datetime.fromisoformat(reminder_at)
        if run_dt <= datetime.now():
            return

        self.scheduler.add_job(
            self._send_reminder,
            trigger="date",
            run_date=run_dt,
            args=[booking_id],
            id=f"reminder_{booking_id}",
            replace_existing=True,
        )

    def remove_booking_job(self, booking_id: int) -> None:
        job_id = f"reminder_{booking_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def restore_jobs(self) -> None:
        # Recreate reminder jobs from DB after bot restart.
        now_iso = datetime.now().isoformat()
        for booking in self.db.get_bookings_for_reminders(now_iso):
            self.schedule_booking(booking["id"], booking["reminder_at"])

    async def _send_reminder(self, booking_id: int) -> None:
        booking = self.db.get_booking_by_id(booking_id)
        if not booking or booking["status"] != "active":
            return

        text = (
            f"Напоминаем, что вы записаны на наращивание ресниц завтра в {booking['slot_time']}.\n"
            "Ждём вас ❤️"
        )
        try:
            await self.bot.send_message(booking["user_id"], text)
        except Exception:
            pass
