from ..utils import redis_func_cache

redis_func_cache.set_config()
import nest_asyncio

nest_asyncio.apply()
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from python_modules import path_setting_funcs

from .global_router import global_router

logging.basicConfig(level=logging.DEBUG)
from python_modules.logger import setup_logging

setup_logging()


# Создание хранилища с Redis
storage = RedisStorage.from_url('redis://localhost:6379/5')


async def run():
    token = path_setting_funcs.get_document_by_key_name('setting.yaml',
    'admin_telegram_bot_api')
    bot = Bot(token=token)
    dp = Dispatcher(storage=storage)
    dp.include_router(global_router)
    await dp.start_polling(bot, skip_updates=True)