"""Shared (paid+free) mode defaults — ``mode-defaults-policy-ownership``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommonModeDefaultsPolicy:
    """Truly shared defaults: A/B Hold всегда выкл по умолчанию."""

    card_ab_hold_mode: str = "off"
