"""Read-only CH адаптеры AI Package v1 export."""

from app.modules.ai_package_v1.readers.ch_campaign_stat_reader import ChCampaignStatReader
from app.modules.ai_package_v1.readers.ch_funnel_reader import ChFunnelReader
from app.modules.ai_package_v1.readers.ch_freshness_reader import ChExportFreshnessReader

__all__ = [
    "ChCampaignStatReader",
    "ChFunnelReader",
    "ChExportFreshnessReader",
]
