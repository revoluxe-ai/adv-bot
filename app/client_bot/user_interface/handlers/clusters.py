import logging

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks, messages

sm = get_async_session_maker


router = Router()


logger = logging.getLogger(__name__)


@router.callback_query(callbacks.TurnClusters.filter(F.action == "on"))
async def turn_clusters_on(
    callback: types.CallbackQuery,
    bot: Bot,
    state: FSMContext,
    callback_data: callbacks.TurnClusters,
) -> None:
    if callback.message is None:
        return
    adv_setting_id = callback_data.adv_original_id
    data = await state.get_data()

    async with sm(read_only=False) as session:
        result_adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_setting_id))
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
        adv_setting.clusters_mode = True
        await session.commit()
    wb_user_cabinet_original_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        result_wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet: WBUserCabinet | None = result_wb_user_cabinet.scalar_one_or_none()
        if wb_user_cabinet is None:
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    assert adv_setting is not None
    assert wb_user_cabinet is not None
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.TurnClusters.filter(F.action == "off"))
async def turn_clusters_off(
    callback: types.CallbackQuery,
    bot: Bot,
    state: FSMContext,
    callback_data: callbacks.TurnClusters,
) -> None:
    if callback.message is None:
        return
    adv_setting_id = callback_data.adv_original_id
    data = await state.get_data()

    async with sm(read_only=False) as session:
        result_adv_setting = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_setting_id))
        adv_setting: AdvSetting | None = result_adv_setting.scalar_one_or_none()
        if adv_setting is None:
            await bot.send_message(callback.message.chat.id, "Настройка рекламы не найдена.")
            return
        adv_setting.clusters_mode = False
        await session.commit()
    wb_user_cabinet_original_id: int = data["last_wb_user_cabinet_original_id"]
    async with sm() as session:
        result_wb_user_cabinet = await session.execute(
            select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        wb_user_cabinet: WBUserCabinet | None = result_wb_user_cabinet.scalar_one_or_none()
        if wb_user_cabinet is None:
            await bot.send_message(callback.message.chat.id, "Кабинет пользователя не найден.")
            return
    assert adv_setting is not None
    assert wb_user_cabinet is not None
    chat_id = callback.message.chat.id
    await messages.AdvSettingMenu(bot, chat_id, wb_user_cabinet, adv_setting)()
