"""ClickHouse repository for append-only campaign settings history.

Spec: campaign-settings-history.
Runtime repository may SELECT/INSERT only. DDL remains migration-control-plane owned.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol

from .domain import (
    HistorySnapshotRow,
    HistoryTimelineItem,
)

_TABLE = "campaign_settings_history"
_DATABASE = "default_db"
_QUALIFIED_TABLE = f"{_DATABASE}.{_TABLE}"
_COLUMNS = [
    "observed_at",
    "snapshot_id",
    "adv_setting_id",
    "wb_cabinet_id",
    "shop_id",
    "adv_id",
    "search_adv_id",
    "schema_version",
    "state_hash",
    "payload_json",
]


class ClickHouseCampaignSettingsHistoryRepository:
    """SELECT/INSERT-only runtime adapter over the application CH client."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client

    async def latest_hashes(
        self,
        wb_cabinet_id: int,
        adv_setting_ids: Sequence[int],
    ) -> Mapping[int, str]:
        if not adv_setting_ids:
            return {}
        query = f"""
SELECT
    adv_setting_id,
    argMax(state_hash, tuple(observed_at, snapshot_id)) AS state_hash
FROM {_QUALIFIED_TABLE}
WHERE wb_cabinet_id = %(wb_cabinet_id)s
  AND adv_setting_id IN %(adv_setting_ids)s
GROUP BY adv_setting_id
ORDER BY adv_setting_id
""".strip()
        result = await self._client.query(
            query,
            parameters={
                "wb_cabinet_id": int(wb_cabinet_id),
                "adv_setting_ids": tuple(int(value) for value in adv_setting_ids),
            },
        )
        latest: dict[int, str] = {}
        for row in result.result_rows:
            if len(row) < 2 or type(row[0]) is not int or not isinstance(row[1], str):
                raise ValueError("invalid campaign settings history latest-hash row")
            latest[row[0]] = row[1]
        return latest

    async def insert_snapshots(
        self,
        rows: Sequence[HistorySnapshotRow],
    ) -> None:
        if not rows:
            return
        data = [
            [
                row.observed_at,
                row.snapshot_id,
                row.adv_setting_id,
                row.wb_cabinet_id,
                row.shop_id,
                row.adv_id,
                row.search_adv_id,
                row.schema_version,
                row.state_hash,
                row.payload_json,
            ]
            for row in rows
        ]
        await self._client.insert(
            _TABLE,
            data,
            column_names=_COLUMNS,
            database=_DATABASE,
        )

    async def timeline(
        self,
        adv_setting_id: int,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[HistoryTimelineItem, ...]:
        query = f"""
SELECT
    observed_at,
    snapshot_id,
    schema_version,
    state_hash,
    payload_json
FROM {_QUALIFIED_TABLE}
WHERE adv_setting_id = %(adv_setting_id)s
  AND observed_at >= %(start_at)s
  AND observed_at < %(end_at)s
ORDER BY observed_at, snapshot_id
""".strip()
        result = await self._client.query(
            query,
            parameters={
                "adv_setting_id": int(adv_setting_id),
                "start_at": start_at,
                "end_at": end_at,
            },
        )
        rows = result.result_rows
        return tuple(
            HistoryTimelineItem(
                observed_at=row[0],
                snapshot_id=str(row[1]),
                schema_version=int(row[2]),
                state_hash=str(row[3]),
                payload_json=str(row[4]),
            )
            for row in rows
        )

    async def timeline_up_to(
        self,
        adv_setting_id: int,
        *,
        end_at: datetime,
    ) -> tuple[HistoryTimelineItem, ...]:
        """
        Snapshots with observed_at < end_at (as-of upper bound, exclusive).

        Used for membership authority: latest snapshot at or before event-day end.
        """
        query = f"""
SELECT
    observed_at,
    snapshot_id,
    schema_version,
    state_hash,
    payload_json
FROM {_QUALIFIED_TABLE}
WHERE adv_setting_id = %(adv_setting_id)s
  AND observed_at < %(end_at)s
ORDER BY observed_at, snapshot_id
""".strip()
        result = await self._client.query(
            query,
            parameters={
                "adv_setting_id": int(adv_setting_id),
                "end_at": end_at,
            },
        )
        rows = result.result_rows
        return tuple(
            HistoryTimelineItem(
                observed_at=row[0],
                snapshot_id=str(row[1]),
                schema_version=int(row[2]),
                state_hash=str(row[3]),
                payload_json=str(row[4]),
            )
            for row in rows
        )
