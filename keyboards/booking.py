from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
