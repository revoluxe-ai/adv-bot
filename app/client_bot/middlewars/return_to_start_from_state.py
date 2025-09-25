from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.client_bot.user_interface.handlers.start_registration_func import start_registration


class ReturnToStart(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,  # type: ignore
        data: dict[str, Any],
    ) -> Any:
        text = event.text
        if text is not None and "/start" in text:
            bot = data["bot"]
            state: FSMContext = data["state"]
            await state.clear()
            message = event
            await start_registration(message, bot, state)
            return

        return await handler(event, data)
