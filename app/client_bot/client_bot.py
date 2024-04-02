import asyncio
import secrets
import string

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from ..utils import redis_func_cache

redis_func_cache.set_config()
from aiohttp import web
import nest_asyncio
nest_asyncio.apply()
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from python_modules import path_setting_funcs
from .global_router import global_router

from python_modules.logger import setup_logging
from app.modules.common_slaves.wildberries.shops_data_updater import consumer as shop_updater

setup_logging()


# Создание хранилища с Redis
storage = RedisStorage.from_url('redis://localhost:6379/0')

path_setting = path_setting_funcs.get_setting_path()

WEB_SERVER_HOST = "127.0.0.1"
# Port for incoming request from reverse proxy. Should be any available port

PORT = path_setting_funcs.get_document_by_key_name (path_setting, 'bot_port')

WEB_SERVER_PORT = PORT


BASE_WEBHOOK_URL = 'https://tiriel.ru'

WEBHOOK_PATH = "/telegram_webhook"
path_setting = path_setting_funcs.get_setting_path()
WEBHOOK_SECRET = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
# WEBHOOK_SECRET = '89779uoiugkftyeoilyeligoyuv'


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
                          secret_token=WEBHOOK_SECRET
                          )
async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    await storage.close()


token = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'client_bot_token')
bot = Bot(token=token)

dp = Dispatcher(storage=storage)
dp.include_router(global_router)

try:
    test_mode = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'test_mode')
except:
    test_mode = False

if not test_mode:
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
        await dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)
    else:
        # Оригинальная логика запуска с вебхуком и дополнительными задачами
        await asyncio.gather(start_web_server(), run_shop_updater())


