from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.dto import AdvDataSnapshotDTO, AdvSettingsSnapshotDTO


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_bids_adapter_legacy_when_flags_off() -> None:
    from app.snapshot_data_updater.adapters.cluster_bids_adapter import (
        ClusterBidsSnapshotAdapter,
    )

    cfg = SnapshotUpdaterConfig(
        cluster_bids_shadow_compare=False,
        cluster_bids_read_from_snapshot=False,
    )
    adapter = ClusterBidsSnapshotAdapter(config=cfg)
    adapter.load_snapshot = AsyncMock(return_value=None)

    adv = MagicMock()
    adv.shop_id = "s1"
    adv.adv_id = 1
    adv.get_keywords = AsyncMock(return_value=[])

    result = await adapter.get_keywords_for_adv(adv)
    adv.get_keywords.assert_awaited_once_with()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_bids_adapter_read_uses_strict_redis_getter() -> None:
    from datetime import UTC, datetime

    from app.snapshot_data_updater.adapters.cluster_bids_adapter import (
        ClusterBidsSnapshotAdapter,
    )
    from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
    from app.snapshot_data_updater.dto import MinBidsSnapshotDTO

    cfg = SnapshotUpdaterConfig(
        cluster_bids_read_from_snapshot=True,
        snapshot_schema_version=1,
    )
    ts = datetime.now(tz=UTC)
    settings = AdvSettingsSnapshotDTO(adv_id=1, shop_id="s1")
    snapshot = AdvDataSnapshotDTO(
        adv_id=1,
        shop_id="s1",
        collected_at=ts,
        expires_at=ts,
        schema_version=1,
        partial=False,
        section_completeness={
            "settings": True,
            "keywords": True,
            "min_bids": True,
            "plan_fact": True,
            "cluster_texts": True,
        },
        settings=settings,
        keywords=[],
        min_bids=MinBidsSnapshotDTO(adv_id=1, coverage_ratio=1.0, cache_hit=True),
    )
    reader = SnapshotReader(config=cfg)
    reader.get_adv_snapshot = AsyncMock(return_value=snapshot)
    adapter = ClusterBidsSnapshotAdapter(reader=reader, config=cfg)

    adv = MagicMock()
    adv.shop_id = "s1"
    adv.adv_id = 1
    redis_getter = AsyncMock(return_value=["kw"])

    result = await adapter.get_keywords_for_adv(adv, redis_getter=redis_getter)
    redis_getter.assert_awaited_once_with()
    assert result == ["kw"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_bids_load_snapshot_disables_stale_enforcement() -> None:
    from app.snapshot_data_updater.adapters.cluster_bids_adapter import (
        ClusterBidsSnapshotAdapter,
    )
    from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader

    reader = MagicMock(spec=SnapshotReader)
    reader.get_adv_snapshot = AsyncMock(return_value=None)
    adapter = ClusterBidsSnapshotAdapter(
        reader=reader,
        config=SnapshotUpdaterConfig(cluster_bids_shadow_compare=True),
    )

    await adapter.load_snapshot("s1", 42)

    reader.get_adv_snapshot.assert_awaited_once_with("s1", 42, enforce_stale=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shadow_with_stale_snapshot_still_uses_redis_keywords() -> None:
    from datetime import UTC, datetime, timedelta

    from app.snapshot_data_updater.adapters.cluster_bids_adapter import (
        ClusterBidsSnapshotAdapter,
    )
    from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
    from app.snapshot_data_updater.cache_errors import CacheStaleError
    from app.snapshot_data_updater.dto import MinBidsSnapshotDTO

    cfg = SnapshotUpdaterConfig(
        cluster_bids_shadow_compare=True,
        snapshot_schema_version=1,
    )
    old_ts = datetime.now(tz=UTC) - timedelta(hours=2)
    settings = AdvSettingsSnapshotDTO(adv_id=1, shop_id="s1")
    snapshot = AdvDataSnapshotDTO(
        adv_id=1,
        shop_id="s1",
        collected_at=old_ts,
        expires_at=old_ts + timedelta(hours=1),
        schema_version=1,
        partial=False,
        section_completeness={
            "settings": True,
            "keywords": True,
            "min_bids": True,
            "plan_fact": True,
            "cluster_texts": True,
        },
        settings=settings,
        keywords=[],
        min_bids=MinBidsSnapshotDTO(adv_id=1, coverage_ratio=1.0, cache_hit=True),
    )

    async def get_adv_snapshot(
        shop_id: str, adv_id: int, *, enforce_stale: bool = True
    ) -> AdvDataSnapshotDTO | None:
        if enforce_stale:
            raise CacheStaleError("would fail cluster_bids")
        return snapshot

    reader = SnapshotReader(config=cfg)
    reader.get_adv_snapshot = get_adv_snapshot  # type: ignore[method-assign]
    adapter = ClusterBidsSnapshotAdapter(reader=reader, config=cfg)

    adv = MagicMock()
    adv.shop_id = "s1"
    adv.adv_id = 1
    redis_getter = AsyncMock(return_value=["kw"])

    result = await adapter.get_keywords_for_adv(adv, redis_getter=redis_getter)

    assert result == ["kw"]
    assert redis_getter.await_count == 2
