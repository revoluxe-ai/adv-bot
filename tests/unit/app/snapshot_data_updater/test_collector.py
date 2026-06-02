from __future__ import annotations

import pytest

from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.collector import AdvDataSnapshotCollector
from app.snapshot_data_updater.dto import AdvSettingsSnapshotDTO, PlanFactSnapshotDTO
from app.snapshot_data_updater.providers import (
    StubClickHouseSnapshotProvider,
    StubPostgresSnapshotProvider,
    StubRedisSnapshotProvider,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_shop_stub_pipeline() -> None:
    shop_id = "shop-x"
    collector = AdvDataSnapshotCollector(
        postgres=StubPostgresSnapshotProvider(
            adv_settings_by_shop={
                shop_id: [
                    AdvSettingsSnapshotDTO(adv_id=99, shop_id=shop_id),
                ]
            }
        ),
        clickhouse=StubClickHouseSnapshotProvider(
            plan_facts_by_shop={
                shop_id: {
                    99: PlanFactSnapshotDTO(adv_id=99, fact_orders=3.0),
                }
            }
        ),
        redis=StubRedisSnapshotProvider(default_cache_hit=True),
        assembler=AdvDataSnapshotAssembler(),
    )
    batch = await collector.collect_shop(shop_id)
    assert batch.shop_id == shop_id
    assert len(batch.snapshots) == 1
    snap = batch.snapshots[0]
    assert snap.adv_id == 99
    assert snap.plan_fact is not None
    assert snap.plan_fact.fact_orders == 3.0
    assert len(snap.keywords) >= 1
