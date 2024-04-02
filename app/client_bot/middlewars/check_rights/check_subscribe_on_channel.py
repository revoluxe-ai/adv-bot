from typing import Callable, Dict, Any, Awaitable
from app.client_bot.const import SUPPORT_CHANNEL_ID
import aiogram
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.client_bot.user_interface.views import messages



class CheckSubscribeOnChannel(BaseMiddleware):

    async def __call__(self,  handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: CallbackQuery, data: Dict[str, Any], ) -> Any:

        bot: aiogram.Bot = data['bot']
        await event.answer()
        user_id = event.from_user.id
        if user_id:
            # Замените CHANNEL_ID на идентификатор вашего канала
            member = await bot.get_chat_member(SUPPORT_CHANNEL_ID, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                await messages.NeedSubscribe(bot, event.message.chat.id)()


                return


        await handler(event, data)
        return