import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from aiogram import Dispatcher, types
from aiohttp import ClientSession
from fastapi import FastAPI, Request, Response
from starlette.staticfiles import StaticFiles

from app.client_bot.bot import get_bot
from app.client_bot.global_router import global_router
from app.client_bot.runner import (
    configure_webhook_for_production,
    ensure_no_webhook_for_polling,
    remove_webhook_on_shutdown,
    run_polling_forever,
)
from app.modules.billing.event_manager.event_manager import BillingEventManager
from app.settings import settings
from app.utils.redis_cache import setup_redis_cache
from app.web.routes.auth import router as web_auth_router
from python_modules.logger import setup_logging

# Import token monitoring system
from app.modules.token_monitoring import (
    initialize_token_monitoring,
    shutdown_token_monitoring,
)

logger = logging.getLogger(__name__)

# TODO: Переделать кнопки в боте на более понятные, чтобы было видно какой режим сейчас включен, на какой переключиться при нажатии

setup_logging()
setup_redis_cache()

bot = get_bot()
billing_event_manager = BillingEventManager()


WEBHOOK_SECRET_TOKEN = settings.WEBHOOK_SECRET


POLLING_MODE = settings.polling_mode


@asynccontextmanager
async def lifespan(app_fast_api: FastAPI):
    try:
        await initialize_token_monitoring(
            enable_decorator_monitoring=True,
            enable_expiration_scheduler=True,
        )
        logger.info("Token monitoring system initialized")
    except Exception as e:
        logger.error("Failed to initialize token monitoring: %s", e)

    app_fast_api.state.dispatcher = None
    app_fast_api.state.polling_task = None

    if POLLING_MODE:
        await ensure_no_webhook_for_polling(bot)
        app_fast_api.state.polling_task = asyncio.create_task(
            run_polling_forever(bot, billing_event_manager, app_fast_api),
            name="telegram-long-polling",
        )
    else:
        await configure_webhook_for_production(bot, billing_event_manager)

    try:
        yield
    finally:
        if POLLING_MODE:
            dp = getattr(app_fast_api.state, "dispatcher", None)
            if dp is not None:
                try:
                    await dp.stop_polling()
                except Exception:
                    logger.exception("stop_polling failed")
            t = app_fast_api.state.polling_task
            if t is not None:
                try:
                    await asyncio.wait_for(t, timeout=120)
                except TimeoutError:
                    logger.warning("Polling task did not finish in time, cancelling")
                    _ = t.cancel()
                    with suppress(asyncio.CancelledError):
                        await t
                except Exception:
                    logger.exception("Polling task failed")
        else:
            try:
                await remove_webhook_on_shutdown(bot)
            except Exception:
                logger.exception("Webhook shutdown failed")

        try:
            await shutdown_token_monitoring()
            logger.info("Token monitoring shutdown completed")
        except Exception as e:
            logger.error("Error during token monitoring shutdown: %s", e)


app = FastAPI(lifespan=lifespan)

_web_static_dir = Path(__file__).resolve().parent / "app" / "web" / "static"
_ = app.mount(
    "/web-static",
    StaticFiles(directory=str(_web_static_dir)),
    name="web_static",
)
_ = app.include_router(web_auth_router)


# Эндпоинты для проверок
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


# POST-обработчик вебхука (в проде задайте WEBHOOK_PATH; иначе дефолт для локальных тестов)
_WEBHOOK_PATH: str = settings.WEBHOOK_PATH or "/webhook"


@app.post(_WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != WEBHOOK_SECRET_TOKEN:
        logger.warning("Неверный Secret Token: %s", token)
        return Response(status_code=403, content="Forbidden")

    update = types.Update.model_validate(await request.json())
    async with ClientSession() as client_session:
        dp = Dispatcher(
            client_session=client_session,
            billing_event_manager=billing_event_manager,
        )
        _ = dp.include_router(global_router)
        await dp.feed_update(bot, update)
    return {"status": "ok"}


# Запуск: всегда uvicorn (HTTP + polling task или webhook в lifespan)
if __name__ == "__main__":
    import uvicorn

    host = settings.TELEGRAM_WEB_HOST
    port = settings.TELEGRAM_WEB_PORT
    logger.info(
        "Старт uvicorn %s:%s POLLING_MODE=%s",
        host,
        port,
        POLLING_MODE,
    )
    uvicorn.run(app, host=host, port=port)
