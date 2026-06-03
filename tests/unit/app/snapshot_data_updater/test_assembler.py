from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.adapters.snapshot_reader import SnapshotReader
from app.snapshot_data_updater.config import SnapshotUpdaterConfig
from app.snapshot_data_updater.freshness_policy import FreshnessPolicy
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    KeywordsWarmupDiagnostics,
    MinBidsSnapshotDTO,
    PlanFactSnapshotDTO,
    SnapshotDiagnostics,
)
from app.snapshot_data_updater.services.calculated_keywords_warmup import (
    CalculatedKeywordsWarmupResult,
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


@pytest.mark.unit
def test_assembler_empty_keywords_after_warmup_cache_hit() -> None:
    assembler = AdvDataSnapshotAssembler()
    settings = AdvSettingsSnapshotDTO(adv_id=10, shop_id="shop-a")
    warmup = CalculatedKeywordsWarmupResult(
        adv_id=10,
        keywords=[],
        source="redis_hit",
        cache_hit=True,
        cache_stale=False,
        duration_ms=1.0,
    )
    snapshot = assembler.assemble_adv_snapshot(
        settings=settings,
        plan_fact=PlanFactSnapshotDTO(adv_id=10, fact_views=100.0),
        keywords=[],
        min_bids=MinBidsSnapshotDTO(adv_id=10, coverage_ratio=1.0, cache_hit=True),
        collected_at=datetime(2026, 1, 1, tzinfo=UTC),
        expires_at=datetime(2026, 1, 2, tzinfo=UTC),
        warmup_result=warmup,
    )
    assert snapshot.section_completeness["keywords"] is True
    assert snapshot.diagnostics.keywords_cache_hit is True
    assert snapshot.diagnostics.keywords.keywords_source == "redis_hit"


@pytest.mark.unit
def test_snapshot_usable_with_empty_keywords_after_cache_hit() -> None:
    assembler = AdvDataSnapshotAssembler()
    settings = AdvSettingsSnapshotDTO(adv_id=10, shop_id="shop-a")
    warmup = CalculatedKeywordsWarmupResult(
        adv_id=10,
        keywords=[],
        source="redis_hit",
        cache_hit=True,
        cache_stale=False,
        duration_ms=1.0,
    )
    ts = datetime.now(tz=UTC)
    snapshot = assembler.assemble_adv_snapshot(
        settings=settings,
        plan_fact=PlanFactSnapshotDTO(adv_id=10, fact_views=100.0),
        keywords=[],
        min_bids=MinBidsSnapshotDTO(adv_id=10, coverage_ratio=1.0, cache_hit=True),
        collected_at=ts,
        expires_at=ts + timedelta(hours=1),
        warmup_result=warmup,
    )
    reader = SnapshotReader(
        config=SnapshotUpdaterConfig(
            snapshot_schema_version=1,
            snapshot_adv_policy=FreshnessPolicy(skip_refresh_sec=300.0, stale_sec=0.0),
        )
    )
    assert reader.is_snapshot_usable(snapshot) is True


@pytest.mark.unit
def test_snapshot_usable_legacy_false_completeness_with_cache_hit_diagnostics() -> None:
    """Снимки до fix assembler: keywords=False в completeness, но hit в diagnostics."""
    ts = datetime.now(tz=UTC)
    settings = AdvSettingsSnapshotDTO(adv_id=10, shop_id="shop-a")
    snapshot = AdvDataSnapshotDTO(
        adv_id=10,
        shop_id="shop-a",
        collected_at=ts,
        expires_at=ts + timedelta(hours=1),
        schema_version=1,
        partial=True,
        section_completeness={
            "settings": True,
            "keywords": False,
            "min_bids": True,
            "plan_fact": True,
            "cluster_texts": False,
        },
        settings=settings,
        keywords=[],
        min_bids=MinBidsSnapshotDTO(adv_id=10, coverage_ratio=1.0, cache_hit=True),
        diagnostics=SnapshotDiagnostics(
            keywords_cache_hit=True,
            keywords=KeywordsWarmupDiagnostics(
                keywords_cache_hit=True,
                keywords_source="redis_hit",
                keywords_count=0,
            ),
        ),
    )
    reader = SnapshotReader(
        config=SnapshotUpdaterConfig(
            snapshot_schema_version=1,
            snapshot_adv_policy=FreshnessPolicy(skip_refresh_sec=300.0, stale_sec=0.0),
        )
    )
    assert AdvDataSnapshotAssembler.keywords_section_complete_from_snapshot(snapshot)
    assert reader.is_snapshot_usable(snapshot) is True


@pytest.mark.unit
def test_assembler_warmup_error_marks_keywords_incomplete() -> None:
    assembler = AdvDataSnapshotAssembler()
    settings = AdvSettingsSnapshotDTO(adv_id=10, shop_id="shop-a")
    warmup = CalculatedKeywordsWarmupResult(
        adv_id=10,
        keywords=[],
        source="error",
        cache_hit=False,
        cache_stale=True,
        duration_ms=1.0,
        error="boom",
    )
    snapshot = assembler.assemble_adv_snapshot(
        settings=settings,
        plan_fact=None,
        keywords=[],
        min_bids=None,
        warmup_result=warmup,
    )
    assert snapshot.section_completeness["keywords"] is False
