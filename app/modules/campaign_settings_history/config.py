"""Environment configuration for campaign settings history updater."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .updater import DEFAULT_INTERVAL_SECONDS


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class CampaignSettingsHistoryConfig:
    """Runtime config. Disabled by default until operator/deploy explicitly enables it."""

    enabled: bool = False
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS

    @classmethod
    def from_env(cls) -> CampaignSettingsHistoryConfig:
        return cls(
            enabled=_env_bool("CAMPAIGN_SETTINGS_HISTORY_ENABLED", False),
            interval_seconds=_env_positive_int(
                "CAMPAIGN_SETTINGS_HISTORY_INTERVAL_SECONDS",
                DEFAULT_INTERVAL_SECONDS,
            ),
        )
