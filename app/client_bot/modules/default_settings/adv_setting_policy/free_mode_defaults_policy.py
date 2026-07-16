"""Free-only mode defaults — ``mode-defaults-policy-ownership``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreeModeDefaultsPolicy:
    """Free overlays: A/B Hold MUST оставаться выкл (не paid automation core)."""

    card_ab_hold_mode: str = "off"
