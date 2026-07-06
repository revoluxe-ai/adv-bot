"""Compatibility wrappers for FREE/PAID campaign mode overlays."""

from app.client_bot.modules.default_settings.adv_setting_policy import (
    apply_free_mode_transition,
    apply_free_defaults_settings_for_adv,
    apply_new_campaign_free_defaults,
    apply_paid_auto_management_transition,
    apply_paid_defaults_settings_for_adv,
)

__all__ = [
    "apply_free_mode_transition",
    "apply_free_defaults_settings_for_adv",
    "apply_new_campaign_free_defaults",
    "apply_paid_auto_management_transition",
    "apply_paid_defaults_settings_for_adv",
]
