from app import redis_func_cache
redis_func_cache.set_config()

import nest_asyncio
from app.wildberries.adv_data_updater import ShopDataUpdater
nest_asyncio.apply()
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from python_modules import path_setting_funcs
from .global_router import global_router
import logging
logging.basicConfig(level=logging.DEBUG)
from aiogram import utils
import asyncio
from app.wildberries.adv_data_updater import consumer as shop_updater
from python_modules.logger import setup_logging


setup_logging()


# Создание хранилища с Redis
storage = RedisStorage.from_url('redis://localhost:6379/0')




async def run():
    token = path_setting_funcs.get_document_by_key_name('setting.yaml', 'client_bot_token')
    bot = Bot(token=token)
    dp = Dispatcher(storage=storage)
    dp.include_router(global_router)
    task = asyncio.create_task(shop_updater())
    async with bot:
        await dp.start_polling(bot, skip_updates=True)
    await task





