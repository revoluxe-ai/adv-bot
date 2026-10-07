"""CH adapter для CampaignSettingsHistoryAsOfPort (read-only)."""

from __future__ import annotations

from datetime import datetime

from app.modules.attribution_facts.ports.campaign_settings_history import (
    CampaignSettingsHistoryAsOfPort,
    HistorySnapshotView,
)
from app.modules.campaign_settings_history.clickhouse_repository import (
    ClickHouseCampaignSettingsHistoryRepository,
)
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol


class CampaignSettingsHistoryAsOfAdapter(CampaignSettingsHistoryAsOfPort):
    """Обёртка над production history repository для membership as-of."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._repo = ClickHouseCampaignSettingsHistoryRepository(client)

    async def snapshots_covering(
        self,
        adv_setting_id: int,
        *,
        range_start: datetime,
        range_end: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        timeline = await self._repo.timeline(
            adv_setting_id,
            start_at=range_start,
            end_at=range_end,
        )
        return tuple(
            HistorySnapshotView(
                snapshot_id=item.snapshot_id,
                observed_at=item.observed_at,
                payload_json=item.payload_json,
            )
            for item in timeline
        )
