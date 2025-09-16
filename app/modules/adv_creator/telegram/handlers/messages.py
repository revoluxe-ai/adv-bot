from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


class NotEnoughMoneyMessage(TextWithKeyboard):
    async def __call__(self, wb_user_cabinet_original_id: int, *args, **kwargs):
        stmt = select(WBUserCabinet.wb_cabinet_id).\
            where(WBUserCabinet.id == wb_user_cabinet_original_id)
        async with sm() as session:
            wb_cabinet_original_id = await session.execute(stmt)
            wb_cabinet_original_id = wb_cabinet_original_id.scalar()
            self.__wb_cabinet_original_id = wb_cabinet_original_id
        await super().__call__()


    text = """
Не достаточно средств для запуска кампаний. Пополните баланс бота.
    """

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()
        button = InlineKeyboardButton(
        text = 'Пополнить баланс',
        callback_data =\
            callbacks.AddBalance(wb_cabinet_original_id=self.__wb_cabinet_original_id).pack(),
        )

        builder.row(button)
        return builder.as_markup()
