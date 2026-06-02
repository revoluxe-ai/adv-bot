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
    adv.get_keywords.assert_awaited_once_with(cache_only=True)
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_bids_adapter_read_uses_cache_only_when_usable() -> None:
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
    fallback = AsyncMock(return_value=["kw"])

    result = await adapter.get_keywords_for_adv(adv, fallback_getter=fallback)
    fallback.assert_awaited_once()
    assert result == ["kw"]
