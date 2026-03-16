import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from database.db import Database
from handlers.admin import get_admin_router
from handlers.booking import get_booking_router
from handlers.common import get_common_router
from keyboards.calendar import get_booking_window
from scheduler.reminder_scheduler import ReminderScheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    db = Database(settings.db_path)
    db.init()
    # Guarantee at least 3 available slots for each day in booking window.
    start, end = get_booking_window()
    db.ensure_min_available_slots(start.isoformat(), end.isoformat(), min_slots_per_day=3)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    reminder_scheduler = ReminderScheduler(bot=bot, db=db, timezone=settings.timezone)
    reminder_scheduler.start()
    await reminder_scheduler.restore_jobs()

    dp.include_router(get_common_router(settings))
    dp.include_router(get_booking_router(settings, db, reminder_scheduler))
    dp.include_router(get_admin_router(settings, db, reminder_scheduler))

    try:
        await dp.start_polling(bot)
    finally:
        reminder_scheduler.shutdown()
        db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
