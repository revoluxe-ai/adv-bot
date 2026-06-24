"""Handlers for the support-channel subscription confirmation flow."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.client_bot.middlewars.channel_subscription import (
    is_user_subscribed_to_support_channel,
)
from app.client_bot.user_interface.handlers.start.start import callback_start_registration
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.messages.messages import NeedSubscribe

router = Router()


@router.callback_query(callbacks.CheckSubscribe.filter())
async def check_subscribe(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Re-check channel membership and continue the normal start flow."""
    if callback.from_user is None:
        return

    subscription_status = await is_user_subscribed_to_support_channel(
        bot,
        callback.from_user.id,
    )
    if subscription_status is not False:
        await callback.answer("Подписка подтверждена")
        await callback_start_registration(callback, bot, state)
        return

    if callback.message is None:
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    await callback.answer(
        "Подписка не найдена. Подпишитесь на канал и повторите проверку.",
        show_alert=True,
    )
    await NeedSubscribe(bot, callback.message.chat.id)()
