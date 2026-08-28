"""Handlers for the support-channel subscription confirmation flow.

CheckSubscribe always revalidates Telegram membership (``force_refresh``) and
treats ``None`` / ``False`` as not confirmed (fail-closed).

ACK: ``ImmediateCallbackAnswerUpdateMiddleware`` на Dispatcher уже вызвал
``callback.answer()`` до handler'а — здесь повторно не отвечаем (см.
``docks/CALLBACK_ANSWER_POLICY.md``).
"""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.client_bot.callback_replay import replay_serialized_callback
from app.client_bot.middlewars.channel_subscription import (
    is_user_subscribed_to_support_channel,
    send_need_subscribe_message,
    send_subscription_check_unavailable_message,
)
from app.client_bot.user_interface.handlers.start.start import callback_start_registration
from app.client_bot.user_interface.views import callbacks

router = Router()


@router.callback_query(callbacks.CheckSubscribe.filter())
async def check_subscribe(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Re-check channel membership and continue the interrupted callback flow.

    Always forces a live Telegram revalidation so a stale positive Redis cache
    cannot confirm subscription. ``None`` (API error) and ``False`` both fail
    closed: no start/replay continuation. ``None`` gets a temporary-check-error
    screen; ``False`` gets the explicit not-subscribed screen.

    Не вызываем ``callback.answer()``: pre-answer middleware уже снял spinner.
    """
    subscription_status = await is_user_subscribed_to_support_channel(
        bot,
        callback.from_user.id,
        force_refresh=True,
    )
    if subscription_status is True:
        state_data = await state.get_data()
        pending_callback = state_data.get("pending_subscription_callback")
        await state.update_data(pending_subscription_callback=None)
        if pending_callback:
            await replay_serialized_callback(
                bot,
                pending_callback,
            )
            return
        await callback_start_registration(callback, bot, state)
        return

    if callback.message is None:
        return

    if subscription_status is None:
        await send_subscription_check_unavailable_message(bot, callback)
    else:
        await send_need_subscribe_message(bot, callback)
