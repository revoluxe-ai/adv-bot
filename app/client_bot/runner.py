"""Telegram bot transport: long polling vs webhook. Used by FastAPI lifespan."""

from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientSession
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from fastapi import FastAPI

from app.client_bot.bot import aclose_telegram_http_session
from app.client_bot.global_router import global_router
from app.modules.billing.event_manager.event_manager import BillingEventManager
from app.settings import settings

logger = logging.getLogger(__name__)


async def ensure_no_webhook_for_polling(bot: Bot) -> None:
    """Delete Telegram webhook before long polling (Telegram allows only one update mode)."""
    logger.info("Удаляем вебхук перед стартом POLLING...")
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            try:
                delete_task = asyncio.create_task(bot.delete_webhook())
                await asyncio.wait_for(delete_task, timeout=5)
                logger.info("Вебхук удалён.")
            except TimeoutError:
                logger.warning(
                    "Таймаут при удалении вебхука. Продолжаем работу.",
                )
        else:
            logger.info("Вебхук не был установлен, пропускаем удаление.")
    except TelegramAPIError as e:
        logger.error("Ошибка при работе с API Telegram: %s", e)
        logger.info("Продолжаем запуск несмотря на ошибку.")
    except Exception as e:
        logger.error("Непредвиденная ошибка при удалении вебхука: %s", e)
        logger.info("Продолжаем запуск несмотря на ошибку.")


async def configure_webhook_for_production(
    bot: Bot,
    billing_event_manager: BillingEventManager,
) -> None:
    """Register Telegram webhook URL (webhook mode only)."""
    async with ClientSession() as client_session:
        dp = Dispatcher(
            client_session=client_session,
            billing_event_manager=billing_event_manager,
        )
        dp.include_router(global_router)
        full_url = (settings.WEBHOOK_URL or "") + (settings.WEBHOOK_PATH or "")
        await bot.set_webhook(
            url=full_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
            secret_token=settings.WEBHOOK_SECRET,
        )
        logger.info("Вебхук установлен: %s", full_url)


async def remove_webhook_on_shutdown(bot: Bot) -> None:
    """Remove webhook and close shared Telegram HTTP session (webhook mode shutdown)."""
    logger.info("Удаление вебхука и закрытие сессии...")
    await bot.delete_webhook()
    await aclose_telegram_http_session()
    logger.info("Webhook shutdown завершён.")


async def run_polling_forever(
    bot: Bot,
    billing_event_manager: BillingEventManager,
    app: FastAPI,
) -> None:
    """Long polling loop; stores ``app.state.dispatcher`` for graceful ``stop_polling``."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        async with ClientSession() as client_session:
            dp = Dispatcher(
                client_session=client_session,
                billing_event_manager=billing_event_manager,
            )
            dp.include_router(global_router)
            app.state.dispatcher = dp
            try:
                logger.info("Запуск бота в режиме POLLING (HTTP сервер уже поднят)...")
                await dp.start_polling(bot)
            finally:
                app.state.dispatcher = None
                await aclose_telegram_http_session()
                logger.info("Сессия long polling / Telegram HTTP завершена.")
