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
    get_coating_type_keyboard,
    get_nail_length_keyboard,
    get_nail_shape_keyboard,
    get_service_categories_keyboard,
    get_services_keyboard,
    get_slots_keyboard,
)
from keyboards.calendar import build_calendar, get_booking_window
from keyboards.main_menu import get_main_menu
from keyboards.subscription import get_subscription_keyboard
from scheduler.reminder_scheduler import ReminderScheduler
from states.booking_states import BookingStates
from utils.formatters import booking_message_html
from utils.pricing import (
    COATING_OPTIONS,
    NAIL_LENGTH_OPTIONS,
    NAIL_SHAPE_OPTIONS,
    get_service_by_id,
    option_label,
)
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

    async def _start_service_flow(message: Message, state: FSMContext) -> None:
        await state.set_state(BookingStates.choosing_service_category)
        await message.answer(
            "<b>Шаг 1/6:</b> Выберите категорию услуги:",
            reply_markup=get_service_categories_keyboard(),
        )

    def _booking_details_html(data: dict) -> str:
        service_name = data.get("service_name", "-")
        service_price = data.get("service_price", 0)
        nail_length = option_label(NAIL_LENGTH_OPTIONS, data.get("nail_length", ""))
        nail_shape = option_label(NAIL_SHAPE_OPTIONS, data.get("nail_shape", ""))
        coating_type = option_label(COATING_OPTIONS, data.get("coating_type", ""))
        comment = data.get("client_comment", "") or "—"
        return (
            f"Услуга: <b>{service_name}</b> ({service_price}₽)\n"
            f"Длина: <b>{nail_length}</b>\n"
            f"Форма: <b>{nail_shape}</b>\n"
            f"Покрытие: <b>{coating_type}</b>\n"
            f"Комментарий: <b>{comment}</b>"
        )

    @router.callback_query(F.data == "menu:book")
    async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
        user_id = callback.from_user.id
        active = db.get_active_booking_by_user(user_id)
        if active:
            await callback.message.answer(
                "У вас уже есть активная запись:\n"
                f"<b>{format_datetime_human(active['work_date'], active['slot_time'])}</b>\n"
                f"{active.get('service_name', 'Услуга')} • {active.get('service_price', 0)}₽\n"
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

        await _start_service_flow(callback.message, state)
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
        await _start_service_flow(callback.message, state)
        await callback.answer()

    @router.callback_query(F.data.startswith("bk:svc_cat:"), BookingStates.choosing_service_category)
    async def choose_service_category(callback: CallbackQuery, state: FSMContext) -> None:
        category_id = callback.data.split(":")[2]
        await state.update_data(service_category=category_id)
        await state.set_state(BookingStates.choosing_service)
        await callback.message.answer(
            "<b>Шаг 2/6:</b> Выберите конкретную услугу:",
            reply_markup=get_services_keyboard(category_id),
        )
        await callback.answer()

    @router.callback_query(F.data == "bk:svc_back", BookingStates.choosing_service)
    async def back_to_categories(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(BookingStates.choosing_service_category)
        await callback.message.answer(
            "Выберите категорию услуги:",
            reply_markup=get_service_categories_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bk:svc:"), BookingStates.choosing_service)
    async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
        _, _, category_id, service_id = callback.data.split(":", 3)
        service = get_service_by_id(category_id, service_id)
        if not service:
            await callback.answer("Услуга не найдена", show_alert=True)
            return

        await state.update_data(
            service_category=category_id,
            service_name=service.title,
            service_price=service.price,
        )
        await state.set_state(BookingStates.choosing_nail_length)
        await callback.message.answer(
            "<b>Шаг 3/6:</b> Какая длина ногтей нужна?",
            reply_markup=get_nail_length_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bk:nlen:"), BookingStates.choosing_nail_length)
    async def choose_nail_length(callback: CallbackQuery, state: FSMContext) -> None:
        option_id = callback.data.split(":")[2]
        await state.update_data(nail_length=option_id)
        await state.set_state(BookingStates.choosing_nail_shape)
        await callback.message.answer(
            "<b>Шаг 4/6:</b> Выберите форму ногтей:",
            reply_markup=get_nail_shape_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bk:nshape:"), BookingStates.choosing_nail_shape)
    async def choose_nail_shape(callback: CallbackQuery, state: FSMContext) -> None:
        option_id = callback.data.split(":")[2]
        await state.update_data(nail_shape=option_id)
        await state.set_state(BookingStates.choosing_coating_type)
        await callback.message.answer(
            "<b>Шаг 5/6:</b> Выберите тип покрытия:",
            reply_markup=get_coating_type_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bk:coat:"), BookingStates.choosing_coating_type)
    async def choose_coating(callback: CallbackQuery, state: FSMContext) -> None:
        option_id = callback.data.split(":")[2]
        await state.update_data(coating_type=option_id)
        await callback.message.answer(
            "<b>Шаг 6/6:</b> Напишите комментарий к записи (дизайн/пожелания) или отправьте '-'",
        )
        await state.set_state(BookingStates.entering_comment)
        await callback.answer()

    @router.message(BookingStates.entering_comment)
    async def enter_comment(message: Message, state: FSMContext) -> None:
        text = (message.text or "").strip()
        client_comment = "" if text == "-" else text
        await state.update_data(client_comment=client_comment)
        await _open_booking_calendar(message, state)

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
            f"{_booking_details_html(data)}\n"
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
            service_category=data.get("service_category", ""),
            service_name=data.get("service_name", ""),
            service_price=int(data.get("service_price", 0)),
            nail_length=data.get("nail_length", ""),
            nail_shape=data.get("nail_shape", ""),
            coating_type=data.get("coating_type", ""),
            client_comment=data.get("client_comment", ""),
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
            f"{format_datetime_human(booking['work_date'], booking['slot_time'])}\n"
            f"{booking.get('service_name', 'Услуга')} • {booking.get('service_price', 0)}₽",
            reply_markup=get_main_menu(user_id == settings.admin_id),
        )

        msg = booking_message_html(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            work_date=booking["work_date"],
            slot_time=booking["slot_time"],
            service_name=booking.get("service_name", ""),
            service_price=int(booking.get("service_price", 0)),
            nail_length=option_label(NAIL_LENGTH_OPTIONS, booking.get("nail_length", "")),
            nail_shape=option_label(NAIL_SHAPE_OPTIONS, booking.get("nail_shape", "")),
            coating_type=option_label(COATING_OPTIONS, booking.get("coating_type", "")),
            comment=booking.get("client_comment", ""),
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
            f"<b>{format_datetime_human(booking['work_date'], booking['slot_time'])}</b>\n"
            f"{booking.get('service_name', 'Услуга')} • {booking.get('service_price', 0)}₽",
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
