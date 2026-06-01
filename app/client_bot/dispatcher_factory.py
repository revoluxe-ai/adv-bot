"""Фабрика Dispatcher клиентского бота с единым порядком middleware."""

from __future__ import annotations

from aiohttp import ClientSession
from aiogram import Dispatcher


from app.client_bot.global_router import global_router
from app.modules.billing.event_manager.event_manager import BillingEventManager


def create_client_bot_dispatcher(
    client_session: ClientSession,
    *,
    billing_event_manager: BillingEventManager,
) -> Dispatcher:
    """Создаёт Dispatcher с middleware для раннего callback answer и global_router."""
    dp = Dispatcher(
        client_session=client_session,
        billing_event_manager=billing_event_manager,
    )
    dp.include_router(global_router)
    return dp
