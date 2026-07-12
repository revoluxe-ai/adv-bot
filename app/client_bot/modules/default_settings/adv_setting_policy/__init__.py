"""Field-policy defaults and mode overlays for ``AdvSetting``."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from .base_policy import AdvSettingDefaultsPolicy
from .common_mode_defaults_policy import CommonCampaignDefaultsPolicy
from .field_policy import FieldPolicy
from .free_mode_defaults_policy import FreeModeDefaultsPolicy
from .paid_mode_defaults_policy import PaidModeDefaultsPolicy
from .white_list_mode_rules import (
    FREE_SAFE_WHITE_LIST_MODES,
)


def apply_common_defaults_settings_for_adv(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Apply common campaign defaults without changing FREE/PAID mode."""
    CommonCampaignDefaultsPolicy.apply(adv_setting, wb_cabinet)


def apply_free_mode_transition(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Переключить РК в FREE mode и применить overlay для spec paid-minus-phrases-default."""
    adv_setting.bot_active = False
    FreeModeDefaultsPolicy.apply(adv_setting, wb_cabinet)


def apply_paid_auto_management_transition(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Переключить РК в PAID mode и применить overlay для spec paid-minus-phrases-default."""
    adv_setting.bot_active = True
    PaidModeDefaultsPolicy.apply(adv_setting, wb_cabinet)


def apply_free_defaults_settings_for_adv(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Backward-compatible alias for the FREE transition helper."""
    apply_free_mode_transition(adv_setting, wb_cabinet)


def apply_paid_defaults_settings_for_adv(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Backward-compatible alias for the PAID transition helper."""
    apply_paid_auto_management_transition(adv_setting, wb_cabinet)


def apply_new_campaign_free_defaults(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Apply common defaults first, then enforce FREE-mode overlay."""
    apply_common_defaults_settings_for_adv(adv_setting, wb_cabinet)
    apply_free_mode_transition(adv_setting, wb_cabinet)


__all__ = [
    "AdvSettingDefaultsPolicy",
    "CommonCampaignDefaultsPolicy",
    "FREE_SAFE_WHITE_LIST_MODES",
    "FieldPolicy",
    "FreeModeDefaultsPolicy",
    "PaidModeDefaultsPolicy",
    "apply_common_defaults_settings_for_adv",
    "apply_free_mode_transition",
    "apply_free_defaults_settings_for_adv",
    "apply_new_campaign_free_defaults",
    "apply_paid_auto_management_transition",
    "apply_paid_defaults_settings_for_adv",
]
