from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить рабочий день", callback_data="admin:action:add_day")
    kb.button(text="Добавить слот", callback_data="admin:action:add_slot")
    kb.button(text="Удалить слот", callback_data="admin:action:delete_slot")
    kb.button(text="Отменить запись клиента", callback_data="admin:action:cancel_booking")
    kb.button(text="Закрыть день", callback_data="admin:action:close_day")
    kb.button(text="Расписание на дату", callback_data="admin:action:view_day")
    kb.button(text="В меню", callback_data="admin:action:back")
    kb.adjust(1)
    return kb.as_markup()


def get_admin_slots_keyboard(action: str, slots: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in slots:
        kb.button(text=slot["slot_time"], callback_data=f"admin:{action}:slot:{slot['id']}")
    kb.button(text="Назад", callback_data="menu:admin")
    kb.adjust(3, 1)
    return kb.as_markup()


def get_admin_bookings_keyboard(bookings: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for booking in bookings:
        service = booking.get("service_name") or "услуга"
        text = f"{booking['slot_time']} • {booking['full_name']} • {service}"
        kb.button(text=text[:40], callback_data=f"admin:cancel_booking:book:{booking['id']}")
    kb.button(text="Назад", callback_data="menu:admin")
    kb.adjust(1)
    return kb.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="В админ-панель", callback_data="menu:admin")
    return kb.as_markup()
