import asyncio
import logging

from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.handlers import start
import aiogram
from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.wb_adv_updater import wb_manager
from app.modules.wb_adv_updater.data_setter import DataSetter
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker
from .. import states

from ..views import callbacks, messages
from app.exc import ApiForbiddenError

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)



@router.callback_query(callbacks.WBUpdate.filter(F.action == 'update_minus_keywords'))
async def update_minus_keywords(callback: types.CallbackQuery,
                                callback_data: callbacks.WBUpdate,
                                bot: aiogram.Bot,
                                state: FSMContext):

    adv_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        adv = await session.execute(select(AdvSetting)\
        .join(AdvSetting.wb_cabinet)\
        .where(AdvSetting.id == adv_original_id))
        adv = adv.scalar()
        wb_cabinet_id: int = adv.wb_cabinet.id
        stmt = select(WBUserCabinet)\
            .join(WBUserCabinet.wb_cabinet)\
        .where(WBCabinet.id == wb_cabinet_id)
        wb_user_cabinet = await session.execute(stmt)
        wb_user_cabinet = wb_user_cabinet.scalar()
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    if not access:
        raise ApiForbiddenError('Не удалось получить доступ к Wildberries')
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    data_setter = DataSetter(access)
    await data_setter.update_minus_keywords_in_adv(adv)
    chat_id = callback.message.chat.id
    await messages.MinusKeywordsUpdated(bot, chat_id)()
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()


@router.callback_query(callbacks.WBUpdate.filter(F.action == 'update_keyword_stat'))
async def update_keyword_stat(callback: types.CallbackQuery,
                                callback_data: callbacks.WBUpdate,
                                bot: aiogram.Bot,
                                state: FSMContext):

        """"
        нужно обновить статистику ключевых слов из Wildberreis, а для этого нужен access
        
        """
        adv_original_id = callback_data.adv_setting_original_id
        async with sm() as session:
            adv: AdvSetting = await session.execute(select(AdvSetting)\
            .join(AdvSetting.wb_cabinet)\
            .where(AdvSetting.id == adv_original_id))
            adv = adv.scalar()
            wb_cabinet_id: int = adv.wb_cabinet.id
            stmt = select(WBUserCabinet)\
                .join(WBUserCabinet.wb_cabinet)\
            .where(WBCabinet.id == wb_cabinet_id)
            wb_user_cabinet = await session.execute(stmt)
            wb_user_cabinet = wb_user_cabinet.scalar()
        access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
        if not access:
            raise ApiForbiddenError('Не удалось получить доступ к Wildberries')
        await messages.LongTimeOperation(bot, callback.message.chat.id)()
        await wb_manager.update_all_keyword_data(access, adv)
        chat_id = callback.message.chat.id
        await messages.KeywordStatUpdated(bot, chat_id)()
        await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()

