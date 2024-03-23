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


WEB_SERVER_HOST = "127.0.0.1"
# Port for incoming request from reverse proxy. Should be any available port
WEB_SERVER_PORT = 8080


BASE_WEBHOOK_URL = 'https://tiriel.ru'
WEBHOOK_PATH = "/telegram_webhook"
path_setting = path_setting_funcs.get_setting_path()
WEBHOOK_SECRET = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)

token = path_setting_funcs.get_document_by_key_name(path_setting,
                                                        'client_bot_token')
bot = Bot(token=token)

dp = Dispatcher(storage=storage)
dp.startup.register(on_startup)
dp.include_router(global_router)


webhook_requests_handler = SimpleRequestHandler(
                            dispatcher=dp,
                            bot=bot,
                            secret_token=WEBHOOK_SECRET)



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


async def run_shop_updater():
    await shop_updater()




async def run():
    await asyncio.gather(start_web_server(),
                         run_shop_updater())




