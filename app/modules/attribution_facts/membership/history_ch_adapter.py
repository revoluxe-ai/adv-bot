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

    async def snapshots_as_of(
        self,
        adv_setting_id: int,
        *,
        as_of_exclusive: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        timeline = await self._repo.timeline_up_to(
            adv_setting_id,
            end_at=as_of_exclusive,
        )
        return tuple(
            HistorySnapshotView(
                snapshot_id=item.snapshot_id,
                observed_at=item.observed_at,
                payload_json=item.payload_json,
            )
            for item in timeline
        )
