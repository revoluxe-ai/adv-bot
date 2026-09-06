"""Compatibility exports for campaign default-setting helpers."""

from app.client_bot.modules.default_settings.adv_setting_policy import (
    apply_common_defaults_settings_for_adv,
    apply_free_mode_transition,
    apply_free_defaults_settings_for_adv,
    apply_new_campaign_free_defaults,
    apply_paid_auto_management_transition,
    apply_paid_defaults_settings_for_adv,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


def apply_defaults_to_adv_setting(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Backward-compatible alias for common campaign defaults.

    Delegates to ``apply_common_defaults_settings_for_adv``, which preserves
    TARGET card_ab_hold §13 freeze/no-op write guards.
    """
    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)


__all__ = [
    "apply_common_defaults_settings_for_adv",
    "apply_free_mode_transition",
    "apply_free_defaults_settings_for_adv",
    "apply_new_campaign_free_defaults",
    "apply_paid_auto_management_transition",
    "apply_paid_defaults_settings_for_adv",
    "apply_defaults_to_adv_setting",
]
