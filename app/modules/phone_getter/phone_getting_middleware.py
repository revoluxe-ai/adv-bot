import typing
from typing import Any, Awaitable, Callable, Dict, Union
from aiogram import BaseMiddleware, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject
from .phone_keyboard import  request_phone_button
from .data_manager import DataManager
from aiogram.types import CallbackQuery
from .text import text


from ...utils.db.models import User

data_manager = DataManager()

class PhoneGetterMiddleWare(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        telegram_object: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        callback = typing.cast(CallbackQuery, telegram_object)
        user_telegram_id = callback.from_user.id
        bot: Bot = data['bot']
        user: User = await data_manager.get_telegram_user_model(user_telegram_id,
                                                                load_only_options=[User.phone])
        if not user.phone:
            await callback.answer('Требуется отправка контакта...')
            message = await bot.send_message(user_telegram_id,
                                   text,
                                   reply_markup = request_phone_button()
                                   )
            state: FSMContext = data['state']
            await state.update_data({'message_id_for_delete': message.message_id})

            return

        # Продолжаем обработку, если пользователь есть и телефон предоставлен
        return await handler(telegram_object, data)


