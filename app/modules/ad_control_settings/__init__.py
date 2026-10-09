"""
Иерархические настройки автоматического рекламного контроля WB Sky (foundation).

Чистый домен: registry, resolver, DRR/headroom state, diagnostics contract.
Без persistence, runtime writers и transport.
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
