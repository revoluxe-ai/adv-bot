from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)


@pytest.mark.unit
def test_calculated_keyword_snapshot_dto_is_slim() -> None:
    kw = CalculatedKeywordSnapshotDTO(
        text="test phrase",
        adv_id=42,
        status=KeywordStatus.GOOD,
        rating=1.5,
        resolved_cpm=200.0,
        views=10,
        clicks=2,
        orders=1,
        spend=50.0,
    )
    data = kw.model_dump()
    assert "keyword_setting" not in data
    assert "cluster_stat" not in data
    assert "cpm_sources" not in data
    assert kw.text == "test phrase"


@pytest.mark.unit
def test_shop_adv_snapshot_batch_roundtrip() -> None:
    ts = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
    settings = AdvSettingsSnapshotDTO(adv_id=1, shop_id="s1")
    snapshot = AdvDataSnapshotDTO(
        adv_id=1,
        shop_id="s1",
        collected_at=ts,
        settings=settings,
    )
    batch = ShopAdvSnapshotBatchDTO(
        shop_id="s1",
        collected_at=ts,
        snapshots=[snapshot],
    )
    assert len(batch.snapshots) == 1
    assert batch.snapshots[0].adv_id == 1
