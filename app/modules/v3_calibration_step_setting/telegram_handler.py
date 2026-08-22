"""Telegram FSM: cap adaptive calibration steps для Авто V3."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update

from app.client_bot.user_interface.handlers.start import start_registration
from app.client_bot.user_interface.views.callbacks import V3CalibrationStepChange
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.v3_calibration_step_ui import (
    FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

MAX_CALIBRATION_STEP = 50

router = Router()


@router.callback_query(V3CalibrationStepChange.filter())
async def change_v3_calibration_step(
    callback: CallbackQuery,
    callback_data: V3CalibrationStepChange,
    state: FSMContext,
) -> None:
    """Запросить новое значение cap шагов калибратора."""
    adv_setting_original_id = callback_data.adv_setting_original_id
    async with sm() as session:
        adv_result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
        )
        adv = adv_result.scalar_one_or_none()
        if adv is None or not adv.bot_active:
            if callback.message is not None:
                await callback.message.answer(
                    "Доступно только при версии АвтоАпдейтера V3."
                )
            return
    await state.update_data(
        {FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID: adv_setting_original_id}
    )
    await state.set_state("waiting_for_v3_calibration_step")
    if callback.message is not None:
        await callback.message.answer(
            f"Введите макс. число effective ladder-шагов калибратора V3 "
            f"(от 0 до {MAX_CALIBRATION_STEP}):"
        )


@router.message(StateFilter("waiting_for_v3_calibration_step"))
async def set_v3_calibration_step(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Сохранить cap и обновить меню РК."""
    data = await state.get_data()
    adv_original_id = data.get(FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID)
    if adv_original_id is None:
        await message.answer("Сессия смены шага истекла. Откройте настройки РК снова.")
        await state.set_state(None)
        return
    text = message.text
    if text == "/start":
        await state.set_state(None)
        await start_registration(message, bot, state)
        return
    if text is None or not text.isdigit():
        await message.answer("Введите целое число от 0 до 50")
        return
    new_step = int(text)
    if new_step < 0 or new_step > MAX_CALIBRATION_STEP:
        await message.answer(
            f"Введите целое число от 0 до {MAX_CALIBRATION_STEP}. "
            "0 — отключить калибратор."
        )
        return
    async with sm(read_only=False) as session:
        await session.execute(
            update(AdvSetting)
            .where(AdvSetting.id == int(adv_original_id))
            .values(keyword_calibration_max_step=new_step)
        )
        await session.commit()
    await message.answer(
        f"Макс. шаг калибратора V3 изменён на {new_step} "
        "(0 — отключить калибратор; далее ×2/÷2 до этого cap)."
    )
    await state.set_state(None)
