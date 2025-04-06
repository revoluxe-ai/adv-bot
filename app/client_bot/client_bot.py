import asyncio
import secrets
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.client_bot.bot import bot

from ..utils import redis_func_cache

redis_func_cache.set_config()
import nest_asyncio
from aiohttp import web
from app import settings
nest_asyncio.apply()
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.strategy import FSMStrategy
from aiogram.fsm.storage.redis import DefaultKeyBuilder

from app.modules.common_slaves.wildberries.shops_data_updater import consumer as shop_updater
from python_modules import path_setting_funcs
from python_modules.logger import setup_logging

from .global_router import global_router

setup_logging()
import os


# Простой эндпоинт для проверки здоровья контейнера
async def health_check(_):
    return web.Response(text="OK", status=200)

# Простой эндпоинт для проверки готовности контейнера
async def readiness_check(_):
    # Можно добавить логику для проверки готовности, например, соединение с базой данных
    return web.Response(text="Ready", status=200)



redis_host = os.environ.get("REDIS_HOST")

# Создание хранилища с Redis
storage = RedisStorage.from_url(f'redis://{redis_host}:6379/0', key_builder=DefaultKeyBuilder(with_destiny=True))

path_setting = path_setting_funcs.get_setting_path()

WEB_SERVER_HOST = "0.0.0.0"
# Port for incoming request from reverse proxy. Should be any available port

PORT = settings.TELEGRAM_WEB_PORT

WEB_SERVER_PORT = PORT


BASE_WEBHOOK_URL = settings.WEBHOOK_URL

WEBHOOK_PATH = settings.WEBHOOK_PATH

WEBHOOK_SECRET = secrets.token_urlsafe(32)

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
                          secret_token=WEBHOOK_SECRET,
                          allowed_updates=dp.resolve_used_update_types())

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    await storage.close()



dp = Dispatcher(
    storage=storage,
    fsm_strategy=FSMStrategy.USER_IN_CHAT,
    events_isolation=SimpleEventIsolation()
)
dp.include_router(global_router)

try:
    test_mode: bool = bool(os.environ.get('TEST_MODE'))
except:
    test_mode = False


polling_mode = settings.polling_mode




if not test_mode and not polling_mode:
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)



webhook_requests_handler = SimpleRequestHandler(
                            dispatcher=dp,
                            bot=bot,
                            secret_token=WEBHOOK_SECRET
)

app = web.Application()

app.router.add_get('/healthz', health_check)
app.router.add_get('/ready', readiness_check)


async def start_web_server():
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    print(f'Server started at http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}')
    print(f'Webhook url: {await bot.get_webhook_info()}')


async def stop_web_server():
    await app.shutdown()
    await app.cleanup()
    await dp.storage.close()



async def run_shop_updater():
    await shop_updater()




async def run():
    await bot.set_my_commands([
        BotCommand(command='start', description='Главное меню/список магазинов/добавить магазин'),

    ]
    )


    if test_mode or polling_mode:
        try:
            await bot.delete_webhook()
        except:
            pass
        # Запускаем бота с пулингом вместо вебхука
        await dp.storage.close()  # Закрываем хранилище перед запуском, чтобы избежать конфликтов
        await asyncio.gather(
             dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)
        )

    else:
    # Оригинальная логика запуска с вебхуком и дополнительными задачами
        await asyncio.gather(start_web_server(), run_shop_updater())


