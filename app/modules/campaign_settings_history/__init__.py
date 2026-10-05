"""Campaign settings history domain.

Spec: campaign-settings-history.
Runtime composition is intentionally not imported here to keep domain imports pure.
"""

from .collector import collect_cabinet
from .domain import (
    CabinetCollectResult,
    CabinetSettingsBatch,
    CampaignSettingsRecord,
    HistorySnapshotRow,
    HistoryTimelineItem,
)

__all__ = [
    "collect_cabinet",
    "CabinetCollectResult",
    "CabinetSettingsBatch",
    "CampaignSettingsRecord",
    "HistorySnapshotRow",
    "HistoryTimelineItem",
]
