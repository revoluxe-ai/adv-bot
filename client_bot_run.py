from app.settings import settings
from python_modules.logger import setup_logging
setup_logging()
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from app.client_bot.bot import get_bot
from app.client_bot.global_router import global_router
import secrets
import string


bot = get_bot()
dp = Dispatcher()
dp.include_router(global_router)

# Генерируем секретный токен для вебхука, используя только допустимые символы
def generate_webhook_token(length=32):
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

WEBHOOK_SECRET_TOKEN = generate_webhook_token()

@asynccontextmanager
async def lifespan(app: FastAPI):
    full_url = settings.WEBHOOK_URL + settings.WEBHOOK_PATH
    await bot.set_webhook(url=full_url,
                          allowed_updates=dp.resolve_used_update_types(),
                          drop_pending_updates=True)
    try:
        yield
    finally:
        await bot.delete_webhook()
        await bot.session.close()


app = FastAPI(lifespan=lifespan)

# Эндпоинт для проверки здоровья контейнера
@app.get("/health")
async def health_check():
    return {"status": "OK"}

# Эндпоинт для проверки готовности контейнера
@app.get("/readiness")
async def readiness_check():
    # Можно добавить логику для проверки готовности, например, соединение с базой данных
    return {"status": "Ready"}

# Эндпоинт для Kubernetes readiness probe
@app.get("/ready")
async def ready_check():
    return {"status": "Ready"}

# Эндпоинт для проверки состояния вебхука
@app.get("/webhook-info")
async def webhook_info():
    webhook_info = await bot.get_webhook_info()
    return {
        "url": webhook_info.url,
        "has_custom_certificate": webhook_info.has_custom_certificate,
        "pending_update_count": webhook_info.pending_update_count,
        "last_error_date": webhook_info.last_error_date,
        "last_error_message": webhook_info.last_error_message,
        "max_connections": webhook_info.max_connections,
        "ip_address": webhook_info.ip_address
    }

@app.post(settings.WEBHOOK_PATH, name="webhook")
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)