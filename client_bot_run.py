import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Dispatcher, types
from aiogram.exceptions import TelegramAPIError
from fastapi import FastAPI, Request
from fastapi import Response

from app.client_bot.bot import get_bot
from app.client_bot.global_router import global_router
from app.settings import settings
from python_modules.logger import setup_logging

logger = logging.getLogger(__name__)


setup_logging()

bot = get_bot()
dp = Dispatcher()
dp.include_router(global_router)

WEBHOOK_SECRET_TOKEN = settings.WEBHOOK_SECRET


POLLING_MODE = settings.polling_mode


@asynccontextmanager
async def lifespan(app_fast_api: FastAPI):
    if POLLING_MODE:
        logger.info("⚙️ POLLING_MODE=True: FastAPI только для health-check и info.")
        yield  # FastAPI просто живёт, бот живёт отдельно
    else:
        full_url = settings.WEBHOOK_URL + settings.WEBHOOK_PATH
        await bot.set_webhook(
            url=full_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
            secret_token=WEBHOOK_SECRET_TOKEN,
        )
        logger.info(f"✅ Вебхук установлен: {full_url}")

        try:
            yield
        finally:
            logger.info("🧹 Удаление вебхука и закрытие сессии...")
            await bot.delete_webhook()
            await bot.session.close()
            logger.info("✅ Завершено.")


app = FastAPI(lifespan=lifespan)


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


# POST-обработчик вебхука
@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != WEBHOOK_SECRET_TOKEN:
        logger.warning(f"⛔ Неверный Secret Token: {token}")
        return Response(status_code=403, content="Forbidden")

    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"status": "ok"}


# Запуск в зависимости от режима
if __name__ == "__main__":
    import uvicorn

    if POLLING_MODE:

        async def start_polling():
            logger.info("🚀 Стартуем в режиме POLLING...")

            # Принудительное удаление вебхука
            logger.info("🧹 Удаляем вебхук перед стартом POLLING...")
            try:
                # Проверяем текущий статус вебхука
                webhook_info = await bot.get_webhook_info()
                if webhook_info.url:
                    # Если вебхук установлен, удаляем его с таймаутом
                    try:
                        # Устанавливаем таймаут в 10 секунд для операции удаления вебхука
                        delete_task = asyncio.create_task(bot.delete_webhook())
                        await asyncio.wait_for(delete_task, timeout=5)
                        logger.info("✅ Вебхук удалён.")
                    except asyncio.TimeoutError:
                        logger.warning(
                            "⚠️ Таймаут при удалении вебхука. Продолжаем работу."
                        )
                else:
                    logger.info("ℹ️ Вебхук не был установлен, пропускаем удаление.")
            except TelegramAPIError as e:
                logger.error(f"❌ Ошибка при работе с API Telegram: {e}")
                logger.info("⚠️ Продолжаем запуск несмотря на ошибку.")
            except Exception as e:
                logger.error(f"❌ Непредвиденная ошибка при удалении вебхука: {e}")
                logger.info("⚠️ Продолжаем запуск несмотря на ошибку.")

            try:
                await dp.start_polling(bot)
            finally:
                await bot.session.close()
                logger.info("✅ Сессия бота завершена.")

        asyncio.run(start_polling())
    else:
        logger.info("🌐 Стартуем FastAPI в режиме WEBHOOK...")
        uvicorn.run(app, host="0.0.0.0", port=8080)
