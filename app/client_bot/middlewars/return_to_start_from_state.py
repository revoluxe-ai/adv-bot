from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.client_bot.start_command import is_start_command_message
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)


class ReturnToStart(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if is_start_command_message(event):
            bot = data["bot"]
            state: FSMContext = data["state"]
            await state.clear()
            message = event
            await start_registration(message, bot, state)
            return

        return await handler(event, data)
