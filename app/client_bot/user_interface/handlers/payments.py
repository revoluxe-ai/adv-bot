from aiogram import Router
import aiogram
from aiogram import types

from app.admin_bot.sender import sender_manager
from app.client_bot.user_interface.views import callbacks, messages
import asyncio


router = Router()



@router.callback_query(callbacks.OrderSubscribe.filter())
async def order_subscribe(callback: types.CallbackQuery,
                          callback_data: callbacks.OrderSubscribe,
                          bot: aiogram.Bot):
    await callback.answer()
    user_telegram_id = callback.message.chat.id
    days = callback_data.period_days
    message_for_admin = f'Заказ от {user_telegram_id} на {days}'


    await asyncio.gather(messages.OrderSubscribe(bot, callback.message.chat.id)(),
                         sender_manager.send_message_to_admin(message_for_admin))





