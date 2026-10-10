"""Unit-тесты классификации DIRECT/LINKED/UNKNOWN."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.attribution_facts.domain.classification import (
    classify_fact_row,
    classify_ordered_nm,
)
from app.modules.attribution_facts.domain.enums import AttributionClass
from app.modules.attribution_facts.domain.models import MembershipSnapshot

pytestmark = pytest.mark.unit

_SHOP = "shop-1"
_ADV = 39900256
_DAY = date(2026, 9, 7)


def _snapshot(promoted: frozenset[int], *, authoritative: bool = True) -> MembershipSnapshot:
    return MembershipSnapshot(
        snapshot_id="snap-1",
        shop_id=_SHOP,
        physical_adv_id=_ADV,
        event_date=_DAY,
        promoted_nm_ids=promoted,
        authoritative=authoritative,
    )


def test_direct_classification() -> None:
    """Promoted nm → DIRECT."""
    assert (
        classify_ordered_nm(837395782, _snapshot(frozenset({837395782})))
        == AttributionClass.DIRECT
    )


def test_linked_classification() -> None:
    """Non-promoted nm при непустом promoted set → LINKED."""
    assert (
        classify_ordered_nm(14824677, _snapshot(frozenset({837395782})))
        == AttributionClass.LINKED
    )


def test_missing_membership_unknown() -> None:
    """Нет snapshot → UNKNOWN."""
    assert classify_ordered_nm(837395782, None) == AttributionClass.UNKNOWN


def test_empty_promoted_unknown_not_linked() -> None:
    """Пустой promoted set → UNKNOWN, не LINKED."""
    assert (
        classify_ordered_nm(14824677, _snapshot(frozenset()))
        == AttributionClass.UNKNOWN
    )


def test_non_authoritative_snapshot_unknown() -> None:
    """Неавторитетный snapshot → UNKNOWN."""
    assert (
        classify_ordered_nm(
            837395782, _snapshot(frozenset({837395782}), authoritative=False)
        )
        == AttributionClass.UNKNOWN
    )


def test_no_direct_fallback_from_linked() -> None:
    """LINKED nm не переклассифицируется в DIRECT без membership."""
    result = classify_ordered_nm(14824677, None)
    assert result != AttributionClass.DIRECT


def test_unsupported_metric_class() -> None:
    """Buyout и пр. → UNSUPPORTED."""
    assert (
        classify_fact_row(1, _snapshot(frozenset({1})), unsupported_metric=True)
        == AttributionClass.UNSUPPORTED
    )
