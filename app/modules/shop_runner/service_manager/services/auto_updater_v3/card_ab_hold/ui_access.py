"""UI helpers paid-only A/B Hold (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)


def is_card_ab_hold_ui_visible(adv_setting: AdvSetting) -> bool:
    """Показывать вход в A/B Hold только при paid bot_active.

    Spec: A/B Hold is paid-only — inactive bot hides entry.
    """
    return bool(adv_setting.bot_active)


def can_enable_card_ab_hold(adv_setting: AdvSetting) -> bool:
    """Разрешить enable A/B Hold только для paid-active кампании."""
    return bool(adv_setting.bot_active)


def card_ab_hold_status_label(adv_setting: AdvSetting) -> str:
    """Текст статуса режима для кнопки меню."""
    mode = normalize_card_ab_hold_mode(
        getattr(adv_setting, "card_ab_hold_mode", None)
    )
    if mode == CardAbHoldMode.ACTIVE:
        return "A/B Hold: ВКЛ"
    if mode == CardAbHoldMode.PENDING_SETUP:
        return "A/B Hold: подготовка…"
    return "A/B Hold: выкл"
