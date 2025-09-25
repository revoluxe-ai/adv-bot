from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from typing import Tuple, Any
from aiogram import Bot

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


class NotEnoughMoneyMessage(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, wb_user_cabinet_original_id: int):
        super().__init__(bot, chat_id)
        self.__wb_cabinet_original_id = wb_user_cabinet_original_id

    async def __call__(self) -> Tuple[Any, str]:
        return await super().__call__()

    text = """
Не достаточно средств для запуска кампаний. Пополните баланс бота.
    """

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        button = InlineKeyboardButton(
            text="Пополнить баланс",
            callback_data=callbacks.AddBalance(wb_cabinet_original_id=self.__wb_cabinet_original_id).pack(),
        )

        builder.row(button)
        return builder.as_markup()
