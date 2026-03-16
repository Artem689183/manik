from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Settings
from keyboards.main_menu import get_main_menu
from utils.pricing import get_price_list_html


def get_common_router(settings: Settings) -> Router:
    router = Router(name="common")

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        is_admin = message.from_user.id == settings.admin_id
        await message.answer(
            "<b>Добро пожаловать!</b>\nВыберите действие:",
            reply_markup=get_main_menu(is_admin),
        )

    @router.callback_query(F.data == "menu:prices")
    async def show_prices(callback: CallbackQuery) -> None:
        await callback.message.answer(get_price_list_html())
        await callback.answer()

    @router.callback_query(F.data == "menu:portfolio")
    async def show_portfolio(callback: CallbackQuery) -> None:
        kb = InlineKeyboardBuilder()
        kb.button(text="Смотреть портфолио", url="https://pin.it/4hf5ALudg")
        markup: InlineKeyboardMarkup = kb.as_markup()
        await callback.message.answer("Портфолио мастера:", reply_markup=markup)
        await callback.answer()

    @router.callback_query(F.data == "ignore")
    async def ignore_callback(callback: CallbackQuery) -> None:
        await callback.answer()

    return router
