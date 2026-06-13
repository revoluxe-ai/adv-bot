"""Telegram UI: toggle V3 Raise MAX (``AdvSetting.v3_substitute_fact_cpo_for_max``)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.callbacks import V3SubstituteFactCpoToggle
from app.modules.common_slaves.wildberries.models import AdvSetting


def v3_substitute_fact_cpo_main_button(adv_setting: AdvSetting) -> InlineKeyboardButton:
    """Кнопка вкл/выкл Raise MAX в меню РК (только V3)."""
    enabled = bool(getattr(adv_setting, "v3_substitute_fact_cpo_for_max", False))
    status = "вкл" if enabled else "выкл"
    return InlineKeyboardButton(
        text=f"V3 Raise MAX: {status}",
        callback_data=V3SubstituteFactCpoToggle(
            adv_setting_original_id=adv_setting.id,
            new_status=not enabled,
        ).pack(),
    )
