import asyncio
import secrets
import string

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

from app.modules.common_slaves.wildberries.shops_data_updater import consumer as shop_updater
from python_modules import path_setting_funcs
from python_modules.logger import setup_logging

from .global_router import global_router

setup_logging()


# Создание хранилища с Redis
storage = RedisStorage.from_url('redis://localhost:6379/0')

path_setting = path_setting_funcs.get_setting_path()

WEB_SERVER_HOST = "127.0.0.1"
# Port for incoming request from reverse proxy. Should be any available port

PORT = 8090

WEB_SERVER_PORT = PORT


BASE_WEBHOOK_URL = 'https://tiriel.ru'

WEBHOOK_PATH = "/telegram_webhook"

WEBHOOK_SECRET = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
# WEBHOOK_SECRET = '89779uoiugkftyeoilyeligoyuv' #для нагрузочных тестов


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
                          secret_token=WEBHOOK_SECRET,
                          allowed_updates=dp.resolve_used_update_types())

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    await storage.close()



dp = Dispatcher(storage=storage)
dp.include_router(global_router)

try:
    test_mode = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'test_mode')
except:
    test_mode = False

try:
    polling_mode = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'polling_mode')
except:
    polling_mode = False



if not test_mode or polling_mode:
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)



webhook_requests_handler = SimpleRequestHandler(
                            dispatcher=dp,
                            bot=bot,
                            secret_token=WEBHOOK_SECRET
)



app = web.Application()
webhook_requests_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)


async def start_web_server():
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
    if test_mode:
        await bot.delete_webhook()
        # Запускаем бота с пулингом вместо вебхука
        await dp.storage.close()  # Закрываем хранилище перед запуском, чтобы избежать конфликтов
        await asyncio.gather(
             run_shop_updater(),
             dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)
        )

    else:
        # Оригинальная логика запуска с вебхуком и дополнительными задачами
        await asyncio.gather(start_web_server(), run_shop_updater())


