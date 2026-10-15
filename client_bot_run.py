import asyncio
import logging
from contextlib import asynccontextmanager

from aiohttp import ClientSession
from aiogram import types
from aiogram.exceptions import TelegramAPIError
from fastapi import FastAPI, Request, Response

from app.client_bot.bot import aclose_telegram_http_session, get_bot
from app.client_bot.dispatcher_factory import create_client_bot_dispatcher
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.modules.billing.event_manager.event_manager import BillingEventManager
from app.modules.token_monitoring import (
    initialize_token_monitoring,
    shutdown_token_monitoring,
)
from app.modules.wb_sky_mcp.config import load_mcp_config
from app.settings import settings
from app.utils.redis_cache import setup_redis_cache
from python_modules.logger import setup_logging

logger = logging.getLogger(__name__)

setup_logging()
setup_redis_cache()

bot = get_bot()
billing_event_manager = BillingEventManager()

WEBHOOK_SECRET_TOKEN = settings.WEBHOOK_SECRET
POLLING_MODE = settings.polling_mode


@asynccontextmanager
async def lifespan(app_fast_api: FastAPI):  # noqa: ARG001
    try:
        await initialize_token_monitoring(
            enable_decorator_monitoring=True,
            enable_expiration_scheduler=True,
        )
        logger.info("✅ Token monitoring system initialized")
    except Exception:
        logger.exception("❌ Failed to initialize token monitoring")

    async with ClientSession() as client_session:
        dp = create_client_bot_dispatcher(
            client_session,
            billing_event_manager=billing_event_manager,
        )

        if POLLING_MODE:
            logger.info("⚙️ POLLING_MODE=True: FastAPI только для health-check и info.")
            yield
        else:
            full_url = settings.WEBHOOK_URL + settings.WEBHOOK_PATH
            await bot.set_webhook(
                url=full_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,
                secret_token=WEBHOOK_SECRET_TOKEN,
            )
            logger.info("✅ Вебхук установлен: %s", full_url)

            try:
                yield
            finally:
                logger.info("🧹 Удаление вебхука и закрытие сессии...")
                await bot.delete_webhook()
                await aclose_telegram_http_session()
                logger.info("✅ Завершено.")

    try:
        await shutdown_token_monitoring()
        logger.info("✅ Token monitoring system shutdown completed")
    except Exception:
        logger.exception("❌ Error during token monitoring shutdown")


app = FastAPI(lifespan=lifespan)
if load_mcp_config().enabled:
    from app.modules.wb_sky_mcp.http import mount_wb_sky_mcp

    mount_wb_sky_mcp(app)


@app.get("/health")
async def health_check():
    return {"status": "OK"}


@app.get("/readiness")
@app.get("/ready")
async def readiness_check():
    return {"status": "Ready"}


@app.get("/webhook-info")
async def webhook_info():
    info = await bot.get_webhook_info()
    return {
        "url": info.url,
        "has_custom_certificate": info.has_custom_certificate,
        "pending_update_count": info.pending_update_count,
        "last_error_date": info.last_error_date,
        "last_error_message": info.last_error_message,
        "max_connections": info.max_connections,
        "ip_address": info.ip_address,
    }


@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != WEBHOOK_SECRET_TOKEN:
        logger.warning("⛔ Неверный Secret Token: %s", token)
        return Response(status_code=403, content="Forbidden")

    update = types.Update.model_validate(await request.json())

    async with ClientSession() as client_session:
        dp = create_client_bot_dispatcher(
            client_session,
            billing_event_manager=billing_event_manager,
        )
        await dp.feed_update(bot, update)

    return {"status": "ok"}


async def start_polling():
    logger.info("🚀 Стартуем в режиме POLLING...")

    logger.info("🧹 Удаляем вебхук перед стартом POLLING...")
    try:
        info = await bot.get_webhook_info()
        if info.url:
            try:
                await asyncio.wait_for(bot.delete_webhook(), timeout=5)
                logger.info("✅ Вебхук удалён.")
            except TimeoutError:
                logger.warning("⚠️ Таймаут при удалении вебхука. Продолжаем работу.")
        else:
            logger.info("ℹ️ Вебхук не был установлен, пропускаем удаление.")
    except TelegramAPIError:
        logger.exception("❌ Ошибка при работе с API Telegram")
        logger.info("⚠️ Продолжаем запуск несмотря на ошибку.")
    except Exception:
        logger.exception("❌ Непредвиденная ошибка при удалении вебхука")
        logger.info("⚠️ Продолжаем запуск несмотря на ошибку.")

    try:
        async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
            async with ClientSession() as client_session:
                dp = create_client_bot_dispatcher(
                    client_session,
                    billing_event_manager=billing_event_manager,
                )
                logger.info("🔄 Запуск бота в режиме POLLING...")
                await dp.start_polling(
                    bot,
                    drop_pending_updates=True,
                    polling_timeout=30,
                )
    finally:
        await aclose_telegram_http_session()
        logger.info("✅ Сессия бота завершена.")


if __name__ == "__main__":
    import uvicorn

    if POLLING_MODE:
        asyncio.run(start_polling())
    else:
        logger.info("🌐 Стартуем FastAPI в режиме WEBHOOK...")
        uvicorn.run(app, host="0.0.0.0", port=8080)
