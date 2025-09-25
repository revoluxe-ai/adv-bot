import logging

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiohttp import ClientSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet, WBUserCabinet
from app.modules.common_slaves.wildberries.wb_api import WBApi
from app.modules.wb_adv_updater import wb_manager
from app.modules.wb_adv_updater.data_setter import DataSetter
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks, messages

sm = get_async_session_maker

router = Router()

logger = logging.getLogger(__name__)


@router.callback_query(callbacks.WBUpdate.filter(F.action == "update_minus_keywords"))
async def update_minus_keywords(
    callback: types.CallbackQuery,
    callback_data: callbacks.WBUpdate,
    bot: aiogram.Bot,
    state: FSMContext,
    client_session: ClientSession,
) -> None:
    adv_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        result = await session.execute(
            select(AdvSetting).join(AdvSetting.wb_cabinet).where(AdvSetting.id == adv_original_id)
        )
        adv = result.scalar_one_or_none()
        if adv is None:
            return
        wb_cabinet_id: int = adv.wb_cabinet.id
        stmt = select(WBUserCabinet).join(WBUserCabinet.wb_cabinet).where(WBCabinet.id == wb_cabinet_id)
        result_user = await session.execute(stmt)
        wb_user_cabinet = result_user.scalar_one_or_none()
        if wb_user_cabinet is None:
            return
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    if not access:
        raise ApiForbiddenError("Не удалось получить доступ к Wildberries")
    if not isinstance(callback.message, types.Message):
        return
    await messages.LongTimeOperation(bot, callback.message.chat.id)()

    wb_api = WBApi(access, client_session)
    data_setter = DataSetter(wb_api)
    wb_cabinet = adv.wb_cabinet
    await data_setter.update_minus_keywords_in_adv(adv, wb_cabinet)
    chat_id = callback.message.chat.id
    await messages.MinusKeywordsUpdated(bot, chat_id)()
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()


@router.callback_query(callbacks.WBUpdate.filter(F.action == "update_keyword_stat"))
async def update_keyword_stat(
    callback: types.CallbackQuery,
    callback_data: callbacks.WBUpdate,
    bot: aiogram.Bot,
    state: FSMContext,
    client_session: ClientSession,
) -> None:
    """
    Нужно обновить статистику ключевых слов из Wildberries; требуется access.
    """
    adv_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        result_adv = await session.execute(
            select(AdvSetting).join(AdvSetting.wb_cabinet).where(AdvSetting.id == adv_original_id)
        )
        adv = result_adv.scalar_one_or_none()
        if adv is None:
            return
        wb_cabinet_id: int = adv.wb_cabinet.id
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)
            .options(selectinload(WBUserCabinet.wb_cabinet))
            .where(WBCabinet.id == wb_cabinet_id)
        )
        result_user = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet | None = result_user.scalar_one_or_none()
    if wb_user_cabinet is None:
        return
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    if not access:
        raise ApiForbiddenError("Не удалось получить доступ к Wildberries")
    if not isinstance(callback.message, types.Message):
        return
    await messages.LongTimeOperation(bot, callback.message.chat.id)()

    wb_cabinet = wb_user_cabinet.wb_cabinet
    wb_api = WBApi(access, client_session)
    await wb_manager.update_all_keyword_data(wb_api, adv, wb_cabinet)
    chat_id = callback.message.chat.id
    await messages.KeywordStatUpdated(bot, chat_id)()
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv)()
