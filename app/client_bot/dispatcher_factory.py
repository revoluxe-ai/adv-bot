"""Фабрика Dispatcher клиентского бота с единым порядком middleware."""

from __future__ import annotations

from aiohttp import ClientSession
from aiogram import Dispatcher

from app.client_bot.global_router import global_router
from app.client_bot.callback_replay import register_dispatcher
from app.client_bot.middlewars.immediate_callback_answer import (
    ImmediateCallbackAnswerUpdateMiddleware,
)
from app.modules.billing.event_manager.event_manager import BillingEventManager


def install_client_bot_dispatcher_middleware(dp: Dispatcher) -> None:
    """Outer middleware: ACK callback до FSM/Scene/Gate (см. docks/CALLBACK_ANSWER_POLICY.md)."""
    dp.update.outer_middleware(ImmediateCallbackAnswerUpdateMiddleware())


def create_client_bot_dispatcher(
    client_session: ClientSession,
    *,
    billing_event_manager: BillingEventManager,
) -> Dispatcher:
    """Создаёт Dispatcher и подключает global_router."""
    dp = Dispatcher(
        client_session=client_session,
        billing_event_manager=billing_event_manager,
    )
    install_client_bot_dispatcher_middleware(dp)
    register_dispatcher(dp)
    dp.include_router(global_router)
    return dp
