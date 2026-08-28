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
    """Apply common campaign defaults without changing FREE/PAID mode.

    Shared defaults / «Применить дефолты» — **не** enable/disable path A/B Hold
    (spec ``card-ab-hold-mode`` «Shared defaults MUST NOT disable or mutate A/B
    Hold on a held campaign» / decision ``card-ab-hold-write-path-ownership`` §13):
    для кампании в ``PENDING_SETUP`` / ``ACTIVE`` функция — **no-op**, чтобы не
    выполнить un-owned disable (mode→off + stale allowed-set snapshot + сброс V3 /
    structural флагов в обход freeze). Отключение A/B Hold — только owned paid
    Telegram EXIT. Для ``OFF`` дефолты применяются как обычно.

    Args:
        adv_setting: Объект AdvSetting, к которому применяются дефолтные настройки
        wb_cabinet: Объект WBCabinet, из которого берем дефолтные настройки
    """
    # Inline-import (документированное исключение no-inline-imports): пакет
    # `default_settings` импортируется очень рано (wb_db_manager / model init), а
    # top-level импорт `auto_updater_v3` вызывает циклический импорт. На runtime
    # (вызов из handler) пакет уже инициализирован.
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
        is_ab_hold_structural_freeze,
    )

    if is_ab_hold_structural_freeze(adv_setting.card_ab_hold_mode):
        return

    CommonCampaignDefaultsPolicy.apply(adv_setting, wb_cabinet)


def apply_free_mode_transition(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Switch the campaign into explicit FREE mode and apply the FREE overlay."""
    adv_setting.bot_active = False
    FreeModeDefaultsPolicy.apply(adv_setting, wb_cabinet)


def apply_paid_auto_management_transition(
    adv_setting: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Switch the campaign into explicit PAID auto-management mode and apply the PAID overlay."""
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
