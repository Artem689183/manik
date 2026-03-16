import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database.db import Database
from keyboards.booking import (
    get_booking_confirm_keyboard,
    get_cancel_booking_keyboard,
    get_slots_keyboard,
)
from keyboards.calendar import build_calendar, get_booking_window
from keyboards.main_menu import get_main_menu
from keyboards.subscription import get_subscription_keyboard
from scheduler.reminder_scheduler import ReminderScheduler
from states.booking_states import BookingStates
from utils.formatters import booking_message_html
from utils.subscription import is_user_subscribed
from utils.validators import format_datetime_human, is_valid_phone

logger = logging.getLogger(__name__)


def get_booking_router(
    settings: Settings, db: Database, reminder_scheduler: ReminderScheduler
) -> Router:
    router = Router(name="booking")

    async def _open_booking_calendar(message: Message, state: FSMContext) -> None:
        start, end = get_booking_window()
        available_dates = db.get_available_dates(start.isoformat(), end.isoformat())
        await state.set_state(BookingStates.choosing_date)
        await message.answer(
            "<b>Выберите дату:</b>",
            reply_markup=build_calendar(
                year=start.year,
                month=start.month,
                callback_prefix="bkcal",
                allowed_dates=available_dates,
            ),
        )

    @router.callback_query(F.data == "menu:book")
    async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        active = db.get_active_booking_by_user(user_id)
        if active:
            await callback.message.answer(
                "У вас уже есть активная запись:\n"
                f"<b>{format_datetime_human(active['work_date'], active['slot_time'])}</b>\n"
                "Сначала отмените текущую запись."
            )
            await callback.answer()
            return

        subscribed = await is_user_subscribed(
            callback.bot, user_id, settings.channel_id, settings.channel_link
        )
        if not subscribed:
            await callback.message.answer(
                "Для записи необходимо подписаться на канал.",
                reply_markup=get_subscription_keyboard(settings.channel_link),
            )
            await callback.answer()
            return

        await _open_booking_calendar(callback.message, state)
        await callback.answer()

    @router.callback_query(F.data == "sub:check")
    async def check_subscription(callback: CallbackQuery, state: FSMContext) -> None:
        subscribed = await is_user_subscribed(
            callback.bot,
            callback.from_user.id,
            settings.channel_id,
            settings.channel_link,
        )
        if not subscribed:
            await callback.answer("Подписка пока не найдена", show_alert=True)
            return
        await callback.message.answer("Подписка подтверждена. Можно записываться.")
        await _open_booking_calendar(callback.message, state)
        await callback.answer()

    @router.callback_query(F.data.startswith("bkcal:"))
    async def process_booking_calendar(callback: CallbackQuery, state: FSMContext) -> None:
        try:
            if not callback.data:
                await callback.answer("Некорректный выбор", show_alert=True)
                return

            data = callback.data.split(":")
            action = data[1] if len(data) > 1 else ""
            start, end = get_booking_window()
            available_dates = db.get_available_dates(start.isoformat(), end.isoformat())

            if action == "close":
                await state.clear()
                await callback.message.answer("Выбор даты закрыт.")
                await callback.answer()
                return

            if action == "n":
                if len(data) < 3:
                    await callback.answer("Некорректный месяц", show_alert=True)
                    return
                ym = data[2]
                year, month = map(int, ym.split("-"))
                await callback.message.edit_reply_markup(
                    reply_markup=build_calendar(
                        year=year,
                        month=month,
                        callback_prefix="bkcal",
                        allowed_dates=available_dates,
                    )
                )
                await callback.answer()
                return

            if action == "d":
                if len(data) < 3:
                    await callback.answer("Некорректная дата", show_alert=True)
                    return

                chosen_date = data[2]
                slots = db.get_available_slots(chosen_date)
                if not slots:
                    await callback.message.answer(
                        f"На дату <b>{chosen_date}</b> сейчас нет свободных слотов. Выберите другой день."
                    )
                    await callback.answer()
                    return

                await state.set_state(BookingStates.choosing_time)
                await state.update_data(chosen_date=chosen_date)
                await callback.message.answer(
                    f"<b>Дата:</b> {chosen_date}\nВыберите время:",
                    reply_markup=get_slots_keyboard(slots),
                )
                await callback.answer()
                return

            await callback.answer()
        except Exception:
            logger.exception("Booking calendar callback failed: %s", callback.data)
            await callback.answer("Ошибка при выборе даты. Попробуйте еще раз.", show_alert=True)

    @router.callback_query(F.data.startswith("bk:slot:"), BookingStates.choosing_time)
    async def choose_slot(callback: CallbackQuery, state: FSMContext) -> None:
        slot_id = int(callback.data.split(":")[2])
        slot = db.get_slot_with_date(slot_id)
        if not slot or slot["is_available"] == 0 or slot["is_closed"] == 1:
            await callback.answer("Слот уже недоступен", show_alert=True)
            return

        await state.update_data(slot_id=slot_id, slot_time=slot["slot_time"])
        await state.set_state(BookingStates.entering_name)
        await callback.message.answer("Введите ваше имя:")
        await callback.answer()

    @router.message(BookingStates.entering_name)
    async def enter_name(message: Message, state: FSMContext) -> None:
        full_name = (message.text or "").strip()
        if len(full_name) < 2:
            await message.answer("Имя слишком короткое. Введите имя снова.")
            return
        await state.update_data(full_name=full_name)
        await state.set_state(BookingStates.entering_phone)
        await message.answer("Введите номер телефона:")

    @router.message(BookingStates.entering_phone)
    async def enter_phone(message: Message, state: FSMContext) -> None:
        phone = (message.text or "").strip()
        if not is_valid_phone(phone):
            await message.answer("Некорректный номер. Пример: +79991234567")
            return

        data = await state.get_data()
        chosen_date = data["chosen_date"]
        slot_time = data["slot_time"]
        full_name = data["full_name"]

        await state.update_data(phone=phone)
        await state.set_state(BookingStates.confirming)
        await message.answer(
            "<b>Подтвердите запись:</b>\n"
            f"Дата: <b>{chosen_date}</b>\n"
            f"Время: <b>{slot_time}</b>\n"
            f"Имя: <b>{full_name}</b>\n"
            f"Телефон: <b>{phone}</b>",
            reply_markup=get_booking_confirm_keyboard(),
        )

    @router.callback_query(F.data == "bk:confirm", BookingStates.confirming)
    async def confirm_booking(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        subscribed = await is_user_subscribed(
            callback.bot, user_id, settings.channel_id, settings.channel_link
        )
        if not subscribed:
            await callback.message.answer(
                "Для записи необходимо подписаться на канал.",
                reply_markup=get_subscription_keyboard(settings.channel_link),
            )
            await callback.answer()
            return

        data = await state.get_data()
        slot_id = int(data["slot_id"])
        full_name = data["full_name"]
        phone = data["phone"]

        now = datetime.now()
        visit_dt = datetime.strptime(
            f"{data['chosen_date']} {data['slot_time']}", "%Y-%m-%d %H:%M"
        )
        reminder_at = None
        if visit_dt - now >= timedelta(hours=24):
            reminder_at = (visit_dt - timedelta(hours=24)).isoformat()

        booking = db.create_booking(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            slot_id=slot_id,
            created_at=now.isoformat(),
            reminder_at=reminder_at,
        )
        if not booking:
            await callback.message.answer(
                "Не удалось создать запись: слот уже занят или у вас есть активная запись."
            )
            await callback.answer()
            await state.clear()
            return

        reminder_scheduler.schedule_booking(booking["id"], booking["reminder_at"])

        await callback.message.answer(
            "✅ Запись подтверждена!\n"
            f"{format_datetime_human(booking['work_date'], booking['slot_time'])}",
            reply_markup=get_main_menu(user_id == settings.admin_id),
        )

        msg = booking_message_html(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            work_date=booking["work_date"],
            slot_time=booking["slot_time"],
        )
        await callback.bot.send_message(settings.admin_id, msg)

        await state.clear()
        await callback.answer()

    @router.callback_query(F.data == "bk:close")
    async def close_booking_flow(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.answer("Действие отменено.")
        await callback.answer()

    @router.callback_query(F.data == "menu:cancel_booking")
    async def ask_cancel_booking(callback: CallbackQuery) -> None:
        booking = db.get_active_booking_by_user(callback.from_user.id)
        if not booking:
            await callback.message.answer("У вас нет активной записи.")
            await callback.answer()
            return
        await callback.message.answer(
            "Отменить запись?\n"
            f"<b>{format_datetime_human(booking['work_date'], booking['slot_time'])}</b>",
            reply_markup=get_cancel_booking_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "bk:cancel_no")
    async def cancel_no(callback: CallbackQuery) -> None:
        await callback.message.answer("Отмена не выполнена.")
        await callback.answer()

    @router.callback_query(F.data == "bk:cancel_yes")
    async def cancel_yes(callback: CallbackQuery) -> None:
        active = db.get_active_booking_by_user(callback.from_user.id)
        if not active:
            await callback.message.answer("Активная запись не найдена.")
            await callback.answer()
            return

        result = db.cancel_booking_by_id(active["id"])
        if not result:
            await callback.message.answer("Не удалось отменить запись.")
            await callback.answer()
            return

        reminder_scheduler.remove_booking_job(active["id"])
        await callback.message.answer("Запись отменена. Слот снова доступен.")
        await callback.bot.send_message(
            settings.admin_id,
            "Клиент отменил запись:\n"
            f"{active['work_date']} {active['slot_time']} • {active['full_name']} ({active['phone']})",
        )
        await callback.answer()

    return router
