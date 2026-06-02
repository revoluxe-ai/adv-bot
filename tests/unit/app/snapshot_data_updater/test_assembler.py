from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.dto import (
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    MinBidsSnapshotDTO,
    PlanFactSnapshotDTO,
)


@pytest.mark.unit
def test_assembler_sets_keywords_cache_hit() -> None:
    assembler = AdvDataSnapshotAssembler()
    settings = AdvSettingsSnapshotDTO(adv_id=10, shop_id="shop-a")
    keywords = [
        CalculatedKeywordSnapshotDTO(
            text="kw",
            adv_id=10,
            status=KeywordStatus.GOOD,
        )
    ]
    snapshot = assembler.assemble_adv_snapshot(
        settings=settings,
        plan_fact=PlanFactSnapshotDTO(adv_id=10, fact_views=100.0),
        keywords=keywords,
        min_bids=MinBidsSnapshotDTO(adv_id=10, cache_hit=True),
        collected_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert snapshot.diagnostics.keywords_cache_hit is True
    assert snapshot.plan_fact is not None
    assert snapshot.plan_fact.fact_views == 100.0
