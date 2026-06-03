"""Telegram UI: ``AdvSetting.keyword_calibration_max_step`` (только V3)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.callbacks import V3CalibrationStepChange
from app.modules.common_slaves.wildberries.models import AdvSetting

FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID = "v3_calibration_step_adv_setting_id"


def v3_calibration_step_main_button(adv_setting: AdvSetting) -> InlineKeyboardButton:
    """Кнопка входа в FSM смены cap шагов калибратора."""
    cur = int(adv_setting.keyword_calibration_max_step)
    return InlineKeyboardButton(
        text=f"V3 cal. шаг: {cur}",
        callback_data=V3CalibrationStepChange(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
