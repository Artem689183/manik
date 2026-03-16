from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database.db import Database
from keyboards.admin import (
    get_admin_bookings_keyboard,
    get_admin_menu,
    get_admin_slots_keyboard,
    get_back_to_admin_keyboard,
)
from keyboards.calendar import build_calendar, get_booking_window
from scheduler.reminder_scheduler import ReminderScheduler
from states.admin_states import AdminStates
from utils.formatters import day_schedule_html
from utils.validators import is_valid_time


def get_admin_router(
    settings: Settings, db: Database, reminder_scheduler: ReminderScheduler
) -> Router:
    router = Router(name="admin")

    def _is_admin(user_id: int) -> bool:
        return user_id == settings.admin_id

    async def _send_admin_calendar(
        callback: CallbackQuery,
        action: str,
        allowed_dates: set[str] | None,
    ) -> None:
        start, _ = get_booking_window()
        await callback.message.answer(
            "<b>Выберите дату:</b>",
            reply_markup=build_calendar(
                year=start.year,
                month=start.month,
                callback_prefix=f"adcal:{action}",
                allowed_dates=allowed_dates,
            ),
        )

    def _window_iso() -> tuple[str, str]:
        start, end = get_booking_window()
        return start.isoformat(), end.isoformat()

    @router.callback_query(F.data == "menu:admin")
    async def open_admin_panel(callback: CallbackQuery, state: FSMContext) -> None:
        if not _is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        await state.clear()
        await callback.message.answer("<b>Админ-панель</b>", reply_markup=get_admin_menu())
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:action:"))
    async def admin_action(callback: CallbackQuery) -> None:
        if not _is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return

        action = callback.data.split(":")[2]
        date_from, date_to = _window_iso()

        if action == "back":
            await callback.message.answer("Возврат в меню.")
            await callback.answer()
            return

        if action == "add_day":
            await _send_admin_calendar(callback, "add_day", None)
        elif action == "add_slot":
            allowed = db.get_dates_with_slots(date_from, date_to) | db.get_available_dates(
                date_from, date_to
            )
            await _send_admin_calendar(callback, "add_slot", allowed if allowed else None)
        elif action == "delete_slot":
            allowed = db.get_dates_with_slots(date_from, date_to)
            if not allowed:
                await callback.message.answer("Нет дат со слотами.")
            else:
                await _send_admin_calendar(callback, "delete_slot", allowed)
        elif action == "cancel_booking":
            allowed = db.get_dates_with_bookings(date_from, date_to)
            if not allowed:
                await callback.message.answer("Нет активных записей на ближайший месяц.")
            else:
                await _send_admin_calendar(callback, "cancel_booking", allowed)
        elif action == "close_day":
            await _send_admin_calendar(callback, "close_day", None)
        elif action == "view_day":
            await _send_admin_calendar(callback, "view_day", None)

        await callback.answer()

    @router.callback_query(F.data.startswith("adcal:"))
    async def admin_calendar(callback: CallbackQuery, state: FSMContext) -> None:
        if not _is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return

        parts = callback.data.split(":")
        action = parts[1]
        step = parts[2]

        if step == "close":
            await callback.message.answer("Выбор даты закрыт.")
            await callback.answer()
            return

        if step == "n":
            ym = parts[3]
            year, month = map(int, ym.split("-"))
            date_from, date_to = _window_iso()
            allowed: set[str] | None = None
            if action == "delete_slot":
                allowed = db.get_dates_with_slots(date_from, date_to)
            elif action == "cancel_booking":
                allowed = db.get_dates_with_bookings(date_from, date_to)
            await callback.message.edit_reply_markup(
                reply_markup=build_calendar(
                    year=year,
                    month=month,
                    callback_prefix=f"adcal:{action}",
                    allowed_dates=allowed,
                )
            )
            await callback.answer()
            return

        chosen_date = parts[3]
        if step != "d":
            await callback.answer()
            return

        if action == "add_day":
            db.add_working_day(chosen_date)
            await callback.message.answer(
                f"Рабочий день <b>{chosen_date}</b> добавлен.",
                reply_markup=get_back_to_admin_keyboard(),
            )
        elif action == "add_slot":
            await state.set_state(AdminStates.waiting_slot_time)
            await state.update_data(chosen_date=chosen_date)
            await callback.message.answer(
                f"Введите время для <b>{chosen_date}</b> в формате HH:MM",
                reply_markup=get_back_to_admin_keyboard(),
            )
        elif action == "delete_slot":
            slots = db.get_slots_by_date(chosen_date)
            if not slots:
                await callback.message.answer("На дату нет слотов.")
            else:
                await callback.message.answer(
                    f"Выберите слот для удаления ({chosen_date}):",
                    reply_markup=get_admin_slots_keyboard("delete_slot", slots),
                )
        elif action == "cancel_booking":
            bookings = db.get_bookings_by_date(chosen_date)
            if not bookings:
                await callback.message.answer("На дату нет активных записей.")
            else:
                await callback.message.answer(
                    f"Выберите запись для отмены ({chosen_date}):",
                    reply_markup=get_admin_bookings_keyboard(bookings),
                )
        elif action == "close_day":
            bookings = db.get_active_bookings_by_date(chosen_date)
            for booking in bookings:
                db.cancel_booking_by_id(booking["id"])
                reminder_scheduler.remove_booking_job(booking["id"])
                await callback.bot.send_message(
                    booking["user_id"],
                    f"Ваша запись на {chosen_date} {booking['slot_time']} отменена администратором.",
                )
            db.close_day(chosen_date)
            await callback.message.answer(
                f"День <b>{chosen_date}</b> закрыт.",
                reply_markup=get_back_to_admin_keyboard(),
            )
        elif action == "view_day":
            schedule = db.get_day_schedule(chosen_date)
            await callback.message.answer(
                day_schedule_html(chosen_date, schedule),
                reply_markup=get_back_to_admin_keyboard(),
            )

        await callback.answer()

    @router.message(AdminStates.waiting_slot_time)
    async def add_slot_time(message: Message, state: FSMContext) -> None:
        if not _is_admin(message.from_user.id):
            await state.clear()
            return
        slot_time = (message.text or "").strip()
        if not is_valid_time(slot_time):
            await message.answer("Неверный формат времени. Используйте HH:MM")
            return

        data = await state.get_data()
        chosen_date = data["chosen_date"]
        db.add_working_day(chosen_date)
        ok = db.add_slot(chosen_date, slot_time)
        await state.clear()

        if ok:
            await message.answer(
                f"Слот <b>{slot_time}</b> добавлен на {chosen_date}.",
                reply_markup=get_back_to_admin_keyboard(),
            )
        else:
            await message.answer(
                "Не удалось добавить слот (возможно, уже существует).",
                reply_markup=get_back_to_admin_keyboard(),
            )

    @router.callback_query(F.data.startswith("admin:delete_slot:slot:"))
    async def delete_slot(callback: CallbackQuery) -> None:
        if not _is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        slot_id = int(callback.data.split(":")[3])
        deleted = db.delete_slot(slot_id)
        if deleted:
            await callback.message.answer("Слот удален.")
        else:
            await callback.message.answer("Слот нельзя удалить: он занят активной записью.")
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:cancel_booking:book:"))
    async def admin_cancel_booking(callback: CallbackQuery) -> None:
        if not _is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        booking_id = int(callback.data.split(":")[3])
        booking = db.get_booking_by_id(booking_id)
        if not booking or booking["status"] != "active":
            await callback.message.answer("Запись не найдена.")
            await callback.answer()
            return

        db.cancel_booking_by_id(booking_id)
        reminder_scheduler.remove_booking_job(booking_id)
        await callback.bot.send_message(
            booking["user_id"],
            f"Ваша запись на {booking['work_date']} {booking['slot_time']} отменена администратором.",
        )
        await callback.message.answer(
            f"Запись клиента отменена ({booking['work_date']} {booking['slot_time']})."
        )
        await callback.answer()

    return router
