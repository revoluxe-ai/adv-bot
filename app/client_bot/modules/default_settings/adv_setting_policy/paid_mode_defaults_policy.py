"""Paid-only mode defaults — ``mode-defaults-policy-ownership``."""

from __future__ import annotations

from dataclasses import dataclass

from app.client_bot.modules.default_settings.adv_setting_policy.common_mode_defaults_policy import (
    CommonModeDefaultsPolicy,
)


@dataclass(frozen=True)
class PaidModeDefaultsPolicy:
    """Paid overlays. ``card_ab_hold_mode`` default «выкл»; UI enable — paid only."""

    card_ab_hold_mode: str = CommonModeDefaultsPolicy().card_ab_hold_mode
