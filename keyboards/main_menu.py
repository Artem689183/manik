from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Записаться", callback_data="menu:book")
    kb.button(text="Отменить запись", callback_data="menu:cancel_booking")
    kb.button(text="Прайс", callback_data="menu:prices")
    kb.button(text="Портфолио", callback_data="menu:portfolio")
    if is_admin:
        kb.button(text="Админ-панель", callback_data="menu:admin")
    kb.adjust(1)
    return kb.as_markup()
