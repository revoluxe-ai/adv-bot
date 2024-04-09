from aiogram import Router
import aiogram
from aiogram import types
from sqlalchemy import select
from app.utils.suffixes import get_day_suffix
from app.admin_bot.sender import sender_manager
from app.client_bot.user_interface.views import callbacks, messages
import asyncio

from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker


sm = get_async_session_maker()

router = Router()



@router.callback_query(callbacks.OrderSubscribe.filter())
async def order_subscribe(callback: types.CallbackQuery,
                          callback_data: callbacks.OrderSubscribe,
                          bot: aiogram.Bot):
    await callback.answer()
    user_telegram_id = callback.message.chat.id
    days = callback_data.period_days
    async with sm() as session:
        stmt = select(User).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user = result.scalars().first()


    message_for_admin = f'Заказ от {user_telegram_id}, ник {user.username} на {get_day_suffix(days)}'


    await asyncio.gather(messages.OrderSubscribe(bot, callback.message.chat.id)(),
                         sender_manager.send_message_to_admin(message_for_admin))





