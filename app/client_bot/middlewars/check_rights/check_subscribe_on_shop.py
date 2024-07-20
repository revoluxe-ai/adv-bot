import datetime
from typing import Any, Awaitable, Callable, Dict

import aiogram
from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from app.client_bot.user_interface.views import messages
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


class CheckSubscribeOnShop(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]],
        Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:

        await event.answer()

        bot: aiogram.Bot = data['bot']
        state: FSMContext = data['state']
        state_data = await state.get_data()
        last_wb_cabinet_original_id = state_data.get('last_wb_cabinet_original_id')
        if last_wb_cabinet_original_id:
            async with sm() as session:
                stmt = select(WBCabinet).where(
                    WBCabinet.id == last_wb_cabinet_original_id)
                result = await session.execute(stmt)
                wb_cabinet: WBCabinet = result.scalar()
            if wb_cabinet:
                if all([wb_cabinet.expiration_time < datetime.datetime.now(),
                wb_cabinet.bonus <= 0,
                wb_cabinet.balance <= 0]):
                    await messages.ExpiredSubscription(bot,
                                                       event.message.chat.id,
                                                       wb_cabinet.id)()
                    return

        await handler(event, data)
        return
