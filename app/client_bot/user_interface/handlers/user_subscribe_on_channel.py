"""Handlers for the support-channel subscription confirmation flow."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.client_bot.callback_replay import replay_serialized_callback
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
    """Re-check channel membership and continue the interrupted callback flow."""
    if callback.from_user is None:
        return

    subscription_status = await is_user_subscribed_to_support_channel(
        bot,
        callback.from_user.id,
    )
    if subscription_status is not False:
        await callback.answer("Подписка подтверждена")
        state_data = await state.get_data()
        pending_callback = state_data.get("pending_subscription_callback")
        await state.update_data(pending_subscription_callback=None)
        if pending_callback:
            await replay_serialized_callback(
                bot,
                pending_callback,
                update_id=callback.message.message_id if callback.message is not None else 0,
            )
            return
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
