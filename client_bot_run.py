from app.settings import settings
from python_modules.logger import setup_logging
setup_logging()
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.client_bot.bot import get_bot
from app.client_bot.global_router import global_router


bot = get_bot()
dp = Dispatcher()
dp.include_router(global_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    full_url = settings.WEBHOOK_URL + settings.WEBHOOK_PATH
    await bot.set_webhook(url=full_url,
                          allowed_updates=dp.resolve_used_update_types(),
                          drop_pending_updates=True,
                          secret_token=settings.TELEGRAM_BOT_TOKEN)
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


@app.post(settings.WEBHOOK_PATH, name="webhook")
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)