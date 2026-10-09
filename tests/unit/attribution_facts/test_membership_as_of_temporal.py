"""Temporal as-of membership regression (Slice B history authority)."""

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
from app.modules.attribution_facts.ingest.pipeline import build_ingest_batch_from_raw_items
from app.modules.attribution_facts.membership.as_of import (
    event_date_observed_upper_bound,
    select_as_of_snapshot,
)
from app.modules.attribution_facts.membership.resolver import MembershipSnapshotResolver
from app.modules.attribution_facts.ports.campaign_settings_history import (
    HistorySnapshotView,
)

pytestmark = pytest.mark.unit

_EVENT_DAY = date(2026, 10, 2)
_FIXTURE = (
    Path(__file__).parent / "fixtures" / "fullstats_apps_nms_sample.json"
)


def _payload(nmids: list[int]) -> str:
    return json.dumps({"schema_version": 1, "campaign": {"nmids": nmids}})


class _AsOfHistory:
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


class _Inventory:
    def __init__(self, nm_ids: tuple[int, ...] | None) -> None:
        self._nm_ids = nm_ids

    async def nm_ids_for_adv(
        self,
        shop_id: str,
        physical_adv_id: int,
    ) -> tuple[int, ...] | None:
        return self._nm_ids


@pytest.mark.asyncio
async def test_a_previous_day_snapshot_authoritative_on_event_day() -> None:
    """Snapshot on prior day, none on event day → prior snapshot selected."""
    snapshots = (
        HistorySnapshotView(
            snapshot_id="day-before",
            observed_at=datetime(2026, 10, 1, 12, 0),  # noqa: DTZ001
            payload_json=_payload([101]),
        ),
    )
    resolver = MembershipSnapshotResolver(
        shop_id="s",
        adv_setting_id=1,
        physical_adv_id=99,
        history_port=_AsOfHistory(snapshots),
        inventory_port=_Inventory((999,)),
    )
    resolved = await resolver.resolve(_EVENT_DAY)
    assert resolved.snapshot is not None
    assert resolved.snapshot.snapshot_id == "day-before"
    assert resolved.snapshot.promoted_nm_ids == frozenset({101})
    assert not resolved.partial_fallback


def test_b_select_latest_eligible_before_event_day_end() -> None:
    """Multiple snapshots before upper bound → latest wins."""
    upper = event_date_observed_upper_bound(date(2026, 9, 7))
    rows = (
        HistorySnapshotView(
            snapshot_id="a",
            observed_at=datetime(2026, 9, 6, 10, 0),  # noqa: DTZ001
            payload_json=_payload([1]),
        ),
        HistorySnapshotView(
            snapshot_id="b",
            observed_at=datetime(2026, 9, 7, 18, 0),  # noqa: DTZ001
            payload_json=_payload([2]),
        ),
    )
    picked = select_as_of_snapshot(rows, date(2026, 9, 7))
    assert picked is not None
    assert picked.snapshot_id == "b"
    assert all(s.observed_at < upper for s in rows if s.snapshot_id != "future")


def test_c_snapshot_after_event_day_upper_bound_not_selected() -> None:
    """observed_at after event-day end → excluded."""
    rows = (
        HistorySnapshotView(
            snapshot_id="future",
            observed_at=datetime(2026, 10, 3, 0, 0),  # noqa: DTZ001
            payload_json=_payload([9]),
        ),
    )
    picked = select_as_of_snapshot(rows, _EVENT_DAY)
    assert picked is None


@pytest.mark.asyncio
async def test_d_history_wins_over_inventory_different_nmids() -> None:
    """History before event day beats inventory nm_ids."""
    snapshots = (
        HistorySnapshotView(
            snapshot_id="hist",
            observed_at=datetime(2026, 10, 1, 8, 0),  # noqa: DTZ001
            payload_json=_payload([837395782]),
        ),
    )
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_AsOfHistory(snapshots),
        inventory_port=_Inventory((111, 222)),
    )
    resolved = await resolver.resolve(_EVENT_DAY)
    assert resolved.snapshot is not None
    assert 837395782 in resolved.snapshot.promoted_nm_ids
    assert 111 not in resolved.snapshot.promoted_nm_ids


@pytest.mark.asyncio
async def test_e_no_eligible_history_inventory_partial() -> None:
    """No history as-of → inventory fallback PARTIAL."""
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_AsOfHistory(()),
        inventory_port=_Inventory((837395782,)),
    )
    resolved = await resolver.resolve(_EVENT_DAY)
    assert resolved.partial_fallback
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    batch = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[0],),
        resolver=resolver,
    )
    assert batch.coverage.status == AttributionCoverageStatus.PARTIAL


@pytest.mark.asyncio
async def test_f_no_history_no_inventory_unknown() -> None:
    """No membership → UNKNOWN facts."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    resolver = MembershipSnapshotResolver(
        shop_id="shop-1",
        adv_setting_id=1,
        physical_adv_id=39900256,
        history_port=_AsOfHistory(()),
        inventory_port=_Inventory(None),
    )
    batch = await build_ingest_batch_from_raw_items(
        shop_id="shop-1",
        raw_items=(raw[0],),
        resolver=resolver,
    )
    assert all(f.attribution_class == AttributionClass.UNKNOWN for f in batch.facts)
    assert (
        AttributionReasonCode.ATTRIBUTION_RELATION_UNKNOWN in batch.reason_codes
        or all(
            f.attribution_class == AttributionClass.UNKNOWN for f in batch.facts
        )
    )
