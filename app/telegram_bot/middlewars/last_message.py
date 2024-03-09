import aiogram
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Awaitable, Callable, Dict, Any, Union
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from aiogram.fsm.context import FSMContext
from session_maker import get_async_session_maker
from .. import redis_manager as __redis_manager
from ..models import User
from ...db.associations import WBUserCabinet




_redis_manager = __redis_manager.RedisManager()


class LastMessageMiddleWare(BaseMiddleware):
    async def __call__(

            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message, data: Dict[str, Any]) -> Any:
        state: Union[FSMContext, None] = data.get('state', None)
        if isinstance(event, aiogram.types.CallbackQuery):
            if state:
                await state.clear()
            chat_id = event.message.chat.id
        elif isinstance(event, aiogram.types.Message):
            chat_id = event.chat.id
            text = event.text
            if text and text.startswith('/'):
                await state.clear()
        else:
            chat_id = event.chat.id
            if state:
                 await state.clear()

        last_message = await _redis_manager.get_last_message(chat_id)
        data['last_message'] = last_message

        response = await handler(event, data)
        if response:
            new_message, message_type = response
            await _redis_manager.set_last_message(new_message, message_type)



