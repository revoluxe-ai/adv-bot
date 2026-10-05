"""Disposable ClickHouse boundary evidence for campaign-settings-history.

Requires the repository destructive-local gate:
- localhost/127.0.0.1:8124
- test_adv_bot_clickhouse
- ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.modules.campaign_settings_history.clickhouse_repository import (
    ClickHouseCampaignSettingsHistoryRepository,
)
from app.modules.campaign_settings_history.domain import HistorySnapshotRow
from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE
from tests.support.rewrite_default_db_ch_client import (
    rewriting_clickhouse_client,
)

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]

_TABLE = f"{ALLOWED_CH_DATABASE}.campaign_settings_history"


async def _prepare_history_table(client: Any) -> None:
    await client.command(
        f"""
CREATE TABLE IF NOT EXISTS {_TABLE}
(
    observed_at DateTime64(3, 'UTC'),
    snapshot_id UUID,
    adv_setting_id UInt64,
    wb_cabinet_id UInt64,
    shop_id String,
    adv_id Nullable(UInt64),
    search_adv_id Nullable(UInt64),
    schema_version UInt16,
    state_hash FixedString(64),
    payload_json String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(observed_at)
ORDER BY (wb_cabinet_id, adv_setting_id, observed_at, snapshot_id)
""".strip()
    )
    await client.command(f"TRUNCATE TABLE {_TABLE}")


@pytest.mark.asyncio
async def test_history_repository_write_persists_real_clickhouse_row(
    clickhouse_client: Any,
) -> None:
    """Boundary write: production-shaped repository insert persists in disposable CH."""
    await _prepare_history_table(clickhouse_client)
    repo = ClickHouseCampaignSettingsHistoryRepository(
        rewriting_clickhouse_client(clickhouse_client)
    )
    snapshot_id = str(uuid.uuid4())
    observed_at = datetime(2026, 10, 5, 1, 2, 3, tzinfo=UTC)
    row = HistorySnapshotRow(
        observed_at=observed_at,
        snapshot_id=snapshot_id,
        adv_setting_id=101,
        wb_cabinet_id=77,
        shop_id="shop-77",
        adv_id=1001,
        search_adv_id=2002,
        schema_version=1,
        state_hash="a" * 64,
        payload_json='{"schema_version":1}',
    )

    await repo.insert_snapshots([row])

    result = await clickhouse_client.query(
        "SELECT adv_setting_id, wb_cabinet_id, state_hash, payload_json "
        f"FROM {_TABLE} WHERE snapshot_id = %(snapshot_id)s",
        parameters={"snapshot_id": snapshot_id},
    )
    assert result.result_rows == [
        (101, 77, "a" * 64, '{"schema_version":1}')
    ]


@pytest.mark.asyncio
async def test_history_repository_reads_latest_and_timeline_from_real_clickhouse(
    clickhouse_client: Any,
) -> None:
    """Boundary read: latest-hash and timeline queries return persisted CH state."""
    await _prepare_history_table(clickhouse_client)
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    first_at = datetime(2026, 10, 5, 1, 0, 0, tzinfo=UTC)
    second_at = datetime(2026, 10, 5, 2, 0, 0, tzinfo=UTC)
    columns = [
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
    await clickhouse_client.insert(
        "campaign_settings_history",
        [
            [
                first_at,
                first_id,
                101,
                77,
                "shop-77",
                1001,
                2002,
                1,
                "a" * 64,
                '{"version":"a"}',
            ],
            [
                second_at,
                second_id,
                101,
                77,
                "shop-77",
                1001,
                2002,
                1,
                "b" * 64,
                '{"version":"b"}',
            ],
        ],
        column_names=columns,
        database=ALLOWED_CH_DATABASE,
    )

    repo = ClickHouseCampaignSettingsHistoryRepository(
        rewriting_clickhouse_client(clickhouse_client)
    )
    latest = await repo.latest_hashes(77, [101])
    timeline = await repo.timeline(
        101,
        start_at=datetime(2026, 10, 5, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 10, 6, 0, 0, 0, tzinfo=UTC),
    )

    assert latest == {101: "b" * 64}
    assert [item.snapshot_id for item in timeline] == [first_id, second_id]
    assert [item.state_hash for item in timeline] == ["a" * 64, "b" * 64]
