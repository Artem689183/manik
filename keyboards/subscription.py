from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_subscription_keyboard(channel_link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Подписаться", url=channel_link)
    kb.button(text="Проверить подписку", callback_data="sub:check")
    kb.adjust(1)
    return kb.as_markup()
