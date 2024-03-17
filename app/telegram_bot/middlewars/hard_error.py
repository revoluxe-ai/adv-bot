from aiogram.dispatcher.middlewares.base import BaseMiddleware
import aiogram
from python_modules import path_setting_funcs
from app.telegram_bot.redis_manager import RedisManager
import traceback

admin_telegram_id = 373435337

rm = RedisManager()

class HardErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: aiogram.types.update.Update, data):

        try:
            await handler(event, data)
        except (KeyboardInterrupt, InterruptedError) as e:
            raise e


