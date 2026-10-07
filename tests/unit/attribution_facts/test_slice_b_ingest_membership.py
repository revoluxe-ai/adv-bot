"""Slice B: raw fullstats, membership resolver, ingest pipeline."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.domain.ingest_models import (
    coverage_for_ingest_source,
)
from app.modules.attribution_facts.ingest.pipeline import (
    build_ingest_batch_from_raw_items,
    collapsed_mapper_only_coverage_status,
)
from app.modules.attribution_facts.ingest.raw_fullstats import (
    fullstats_item_to_raw_rows,
)
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.campaign_settings_history import (
    HistorySnapshotView,
)

pytestmark = pytest.mark.unit

_FIXTURE = Path(__file__).parent / "fixtures" / "fullstats_apps_nms_sample.json"
_DAY = date(2026, 9, 7)


class _InMemoryHistory:
    def __init__(self, snapshots: tuple[HistorySnapshotView, ...]) -> None:
        self._snapshots = snapshots

    async def snapshots_as_of(
        self,
        adv_setting_id: int,
        *,
        as_of_exclusive: datetime,
    ) -> tuple[HistorySnapshotView, ...]:
        return tuple(
            s for s in self._snapshots if s.observed_at < as_of_exclusive
        )


class _InMemoryInventory:
    def __init__(self, nm_ids: tuple[int, ...] | None) -> None:
        self._nm_ids = nm_ids

    async def nm_ids_for_adv(
        self,
        shop_id: str,
        physical_adv_id: int,
    ) -> tuple[int, ...] | None:
        return self._nm_ids


def _payload(nmids: list[int]) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "campaign": {"nmids": nmids},
        }
    )


def test_s08_raw_apps_nms_preserved() -> None:
    """S08: apps/nms разворачиваются с app_type и physical adv_id."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    rows = fullstats_item_to_raw_rows(raw[0])
    assert len(rows) >= 3
    app_types = {row.app_type for row in rows}
    assert app_types == {1, 2}
    assert {row.physical_adv_id for row in rows} == {39900256}
    assert any(row.ordered_nm_id == 14824677 for row in rows)


def test_s09_collapsed_mapper_cannot_complete() -> None:
    """S09: DayStats-only ingest coverage не COMPLETE."""
    cov = coverage_for_ingest_source(
        has_raw_nm_rows=False,
        partial_membership_fallback=False,
        all_days_reconciled=True,
    )
    assert cov.status != AttributionCoverageStatus.COMPLETE
    assert collapsed_mapper_only_coverage_status() == "PARTIAL"


@pytest.mark.asyncio
async def test_s05_history_precedence_over_inventory() -> None:
    """S05: history as-of wins (incl. prior-day snapshot); inventory не используется."""
    history = _InMemoryHistory(
        (
            HistorySnapshotView(
                snapshot_id="prior-day",
                observed_at=datetime(2026, 9, 6, 15, 0),  # noqa: DTZ001
                payload_json=_payload([837395782]),
            ),
        )
    )
    inventory = _InMemoryInventory((999,))
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=history,
        inventory_port=inventory,
    )
    resolved = await resolver.resolve(_DAY)
    assert resolved.snapshot is not None
    assert 837395782 in resolved.snapshot.promoted_nm_ids
    assert not resolved.partial_fallback


@pytest.mark.asyncio
async def test_s06_inventory_fallback_partial() -> None:
    """S06: inventory fallback → PARTIAL coverage (not COMPLETE)."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_InMemoryHistory(()),
        inventory_port=_InMemoryInventory((837395782,)),
    )
    resolved = await resolver.resolve(_DAY)
    assert resolved.partial_fallback
    assert (
        AttributionReasonCode.ATTRIBUTION_SOURCE_PARTIAL in resolved.reason_codes
    )
    batch = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[0],),
        resolver=resolver,
    )
    assert batch.partial_membership_fallback
    assert batch.coverage.status == AttributionCoverageStatus.PARTIAL
    assert batch.coverage.status != AttributionCoverageStatus.COMPLETE


@pytest.mark.asyncio
async def test_s07_missing_membership_fail_closed() -> None:
    """S07: нет history/inventory → UNKNOWN classification в batch."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_InMemoryHistory(()),
        inventory_port=_InMemoryInventory(None),
    )
    batch = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[0],),
        resolver=resolver,
    )
    assert batch.used_raw_apps_nms
    assert all(
        fact.attribution_class == AttributionClass.UNKNOWN for fact in batch.facts
    )


@pytest.mark.asyncio
async def test_physical_adv_ids_remain_separate_in_batch() -> None:
    """Auto/Search adv ids — отдельные ingest batches."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    history = _InMemoryHistory(
        (
            HistorySnapshotView(
                snapshot_id="h1",
                observed_at=datetime(2026, 9, 7, 12, 0),  # noqa: DTZ001
                payload_json=_payload([837395782, 111]),
            ),
        )
    )
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=history,
        inventory_port=None,
    )
    batch_a = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[0],),
        resolver=resolver,
    )
    resolver_b = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=2,
        physical_adv_id=39900999,
        history_port=history,
        inventory_port=None,
    )
    batch_b = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[1],),
        resolver=resolver_b,
    )
    adv_ids_a = {f.key.physical_adv_id for f in batch_a.facts}
    adv_ids_b = {f.key.physical_adv_id for f in batch_b.facts}
    assert adv_ids_a == {39900256}
    assert adv_ids_b == {39900999}
