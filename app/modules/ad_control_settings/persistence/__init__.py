"""
PostgreSQL persistence для configured ad control settings (Slice B).

JSONB — только representation; доменная валидация через ``FEATURE_REGISTRY``.
"""

from app.modules.ad_control_settings.persistence.models import (
    AdControlCampaignFeatureRow,
    AdControlShopFeatureRow,
)

__all__ = [
    "AdControlCampaignFeatureRow",
    "AdControlShopFeatureRow",
    "AdControlSettingsRepository",
]


def __getattr__(name: str) -> object:
    if name == "AdControlSettingsRepository":
        from app.modules.ad_control_settings.persistence.repository import (
            AdControlSettingsRepository,
        )

        return AdControlSettingsRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
