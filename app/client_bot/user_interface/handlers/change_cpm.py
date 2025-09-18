from typing import Any

import aiogram
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.bidder.wb_api import WBApi as BidderWBApi
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(callbacks.ChangeCPM.filter())
async def change_cpm(
    callback: aiogram.types.CallbackQuery,
    callback_data: callbacks.ChangeCPM,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Обработчик запроса на изменение CPM."""
    adv_setting_original_id = callback_data.adv_setting_original_id
    await state.update_data(last_adv_setting_original_id=adv_setting_original_id)
    await state.set_state(states.ChangeCPM.waiting_for_cpm)
    await bot.send_message(callback.from_user.id, "Введите новое значение CPM")


@router.message(StateFilter(states.ChangeCPM.waiting_for_cpm))
async def new_cpm_handler(message: aiogram.types.Message, state: FSMContext) -> None:
    """Обработчик ввода нового значения CPM."""
    data: dict[str, Any] = await state.get_data()
    adv_setting_original_id: int | str | None = data.get("last_adv_setting_original_id")
    if not adv_setting_original_id:
        raise Exception("adv_setting_original_id is None")
    adv_setting_original_id = int(adv_setting_original_id)
    cpm = message.text
    if not cpm or not cpm.isdigit():
        await message.answer("CPM должен быть числом")
        return
    cpm_value = int(cpm)
    if cpm_value > 3000:
        await message.answer(
            "Внимание! Системное ограничение: нельзя задать ставку больше 1500. Если нужно снять ограничение, обратитесь к администратору"
        )
        return

    await state.set_state(None)
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .options(joinedload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == int(adv_setting_original_id))
        )
        adv_setting: AdvSetting | None = (await session.execute(stmt)).scalar()
        if not adv_setting:
            await message.answer("Настройка рекламы не найдена")
            return
        shop_id = adv_setting.wb_cabinet.shop_id
        if not shop_id:
            raise Exception("Shop id is None")
        access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)

    # Работа с API вне контекста сессии
    wb_api = BidderWBApi(access)
    try:
        nmid = adv_setting.nmids[0]
        await wb_api.update_cpm(adv_setting.adv_id, nmid, cpm_value)
        await message.answer(f"CPM Авто на {cpm_value}")

        adv_id: int | None = adv_setting.search_adv_id
        if adv_id:
            await wb_api.update_cpm(adv_id, nmid, cpm_value)
            await message.answer(f"CPM Поиск на {cpm_value}")
    except Exception as e:
        await message.answer(f"Ошибка при обновлении ставки на стороне WB (error: {e})")
        return
