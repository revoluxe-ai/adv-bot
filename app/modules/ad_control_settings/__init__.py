"""
Иерархические настройки автоматического рекламного контроля WB Sky (foundation).

Домен, persistence и read-only runtime (shop DRR/headroom/CPO).
Telegram-экран 4.2A читает configured/effective state и dry-run и не пишет слоты.
Runtime не вызывает Apply и не входит в транспорт экрана.
"""

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    AdControlScope,
    ControlPathKind,
    DataSufficiency,
    EffectiveSourceKind,
)
from app.modules.ad_control_settings.domain.resolver import AdControlSettingsResolver

__all__ = [
    "AdControlFeatureId",
    "AdControlFeatureMode",
    "AdControlScope",
    "AdControlSettingsResolver",
    "CampaignRef",
    "ControlPathKind",
    "DataSufficiency",
    "EffectiveSourceKind",
]
