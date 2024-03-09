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
        except Exception as e:
            bot: aiogram.Bot = data['bot']
            if isinstance(event, aiogram.types.Message):
                chat_id = event.chat.id
            else:
                chat_id = event.message.chat.id
            await bot.send_message(chat_id=chat_id,
                             text='Произошла ошибка, администратор уже уведомлен. Попробуйте позже')
            trace_error = traceback.format_exc()
            await bot.send_message(chat_id=admin_telegram_id,
                             text=f'Произошла ошибка: {e}, traceback: {trace_error}')


