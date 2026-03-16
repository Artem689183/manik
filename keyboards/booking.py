from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.pricing import (
    COATING_OPTIONS,
    NAIL_LENGTH_OPTIONS,
    NAIL_SHAPE_OPTIONS,
    SERVICE_CATALOG,
)


def get_service_categories_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for category in SERVICE_CATALOG:
        kb.button(text=category.title, callback_data=f"bk:svc_cat:{category.id}")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(1)
    return kb.as_markup()


def get_services_keyboard(category_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    category = next((c for c in SERVICE_CATALOG if c.id == category_id), None)
    if category:
        for service in category.services:
            kb.button(
                text=f"{service.title} • {service.price}₽",
                callback_data=f"bk:svc:{category_id}:{service.id}",
            )
    kb.button(text="Назад", callback_data="bk:svc_back")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(1)
    return kb.as_markup()


def get_nail_length_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for option_id, label in NAIL_LENGTH_OPTIONS:
        kb.button(text=label, callback_data=f"bk:nlen:{option_id}")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def get_nail_shape_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for option_id, label in NAIL_SHAPE_OPTIONS:
        kb.button(text=label, callback_data=f"bk:nshape:{option_id}")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def get_coating_type_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for option_id, label in COATING_OPTIONS:
        kb.button(text=label, callback_data=f"bk:coat:{option_id}")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def get_slots_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in slots:
        kb.button(text=slot["slot_time"], callback_data=f"bk:slot:{slot['id']}")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(3, 1)
    return kb.as_markup()


def get_booking_confirm_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить", callback_data="bk:confirm")
    kb.button(text="Отмена", callback_data="bk:close")
    kb.adjust(2)
    return kb.as_markup()


def get_cancel_booking_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отменить", callback_data="bk:cancel_yes")
    kb.button(text="Нет", callback_data="bk:cancel_no")
    kb.adjust(2)
    return kb.as_markup()
