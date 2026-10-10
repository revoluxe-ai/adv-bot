"""
Иерархические настройки автоматического рекламного контроля WB Sky (foundation).

Домен, persistence, read-only runtime (shop DRR/headroom/CPO) и Telegram 4.2A.
Runtime не пишет в WB и не вызывает Apply. Экран 4.2A не является runtime writer.
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
