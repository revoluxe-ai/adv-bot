"""
Иерархические настройки автоматического рекламного контроля WB Sky (foundation).

Домен и persistence configured policy, плюс Telegram-экран 4.2A
(чтение и dry-run). Экран не вызывает Apply и не пишет слоты.
Runtime-экономика (DRR/headroom/CPO) в этот транспорт не входит.
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
