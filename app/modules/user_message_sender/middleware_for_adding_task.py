from typing import Any, Awaitable, Callable, Dict
import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ...utils import redis_manager

logger = logging.getLogger(__name__)

class AddingMessageTaskMiddleWare(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user_telegram_id = event.from_user.id
        await redis_manager.set_last_user_use_time(user_telegram_id)
        await handler(event, data)


        return
