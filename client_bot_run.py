from fastapi.openapi.models import Response
from app.settings import settings
from python_modules.logger import setup_logging

setup_logging()

from aiogram import Dispatcher, types
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.client_bot.bot import get_bot
from app.client_bot.global_router import global_router

bot = get_bot()
dp = Dispatcher()
dp.include_router(global_router)

# Генерация секретного токена
WEBHOOK_SECRET_TOKEN = settings.WEBHOOK_SECRET


@asynccontextmanager
async def lifespan(app: FastAPI):
    full_url = settings.WEBHOOK_URL + settings.WEBHOOK_PATH
    await bot.set_webhook(
        url=full_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
        secret_token=WEBHOOK_SECRET_TOKEN,
    )
    print("✅ Вебхук установлен:", full_url)
    try:
        yield
    finally:
        print("🧹 Удаление вебхука...")
        await bot.delete_webhook()
        await bot.session.close()
        print("✅ Вебхук удалён и сессия закрыта.")



app = FastAPI(lifespan=lifespan)

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(
        url=settings.full_webhook_url,
        secret_token=settings.WEBHOOK_SECRET,
    )
    logger.info("✅ Вебхук установлен: {}", settings.full_webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
    logger.info("🛑 Сессия бота закрыта")



# Эндпоинты для проверок
@app.get("/health")
async def health_check():
    return {"status": "OK"}

@app.get("/readiness")
async def readiness_check():
    return {"status": "Ready"}

@app.get("/ready")
async def ready_check():
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

# Основной POST-обработчик вебхука
@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != WEBHOOK_SECRET_TOKEN:
        # можно добавить логирование, чтобы понять кто ломится
        return Response(status_code=403, content="Forbidden")

    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"status": "ok"}


@app.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != WEBHOOK_SECRET_TOKEN:
        # можно добавить логирование, чтобы понять кто ломится
        return Response(status_code=403, content="Forbidden")

    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
