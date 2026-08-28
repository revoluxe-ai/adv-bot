"""Callback handler for admin UI mode switching."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dependency_injector.wiring import Provide, inject

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.ui_mode import UiModeService
from app.client_bot.user_interface.views.callbacks import UiModeToggle
from app.modules.shop_menu.message import ShopMenu
from app.core.redis_manager_v2.redis_client import RedisClient

router = Router()


@router.callback_query(UiModeToggle.filter())
@inject
async def toggle_ui_mode(
    callback_query: CallbackQuery,
    callback_data: UiModeToggle,
    bot: Bot,
    state: FSMContext,
    redis_client: RedisClient | None = Provide["redis_client_wrapper"],
) -> None:
    """Toggle the admin-selected UI mode and rerender the shop menu."""
    if callback_query.message is None:
        return
    user_telegram_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    if not is_bot_admin(user_telegram_id):
        await bot.send_message(chat_id, "Режим интерфейса доступен только админу.")
        return
    if redis_client is None:
        return

    service = UiModeService(redis_client=redis_client)
    next_mode = await service.toggle_user_ui_mode(user_telegram_id)
    await bot.send_message(chat_id, f"Режим интерфейса переключён: {next_mode.upper()}")
    await state.clear()
    await ShopMenu(bot, chat_id, state, callback_data.wb_user_cabinet_original_id)()
