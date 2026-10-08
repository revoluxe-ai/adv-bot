"""observation_id = canonical semantic content hash."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.attribution_facts.domain.enums import AttributionClass, SourceFamily
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionFactKey,
    AttributionMetrics,
    ObservationProvenance,
)
from app.modules.attribution_facts.domain.observation_identity import (
    semantic_observation_id,
)

pytestmark = pytest.mark.unit

_DAY = datetime(2026, 9, 7).date()
_BASE_KEY = AttributionFactKey(
    shop_id="shop",
    physical_adv_id=1,
    event_date=_DAY,
    app_type=1,
    ordered_nm_id=100,
    source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
)
_PROV = ObservationProvenance(
    observation_id="ignored",
    source_revision=1,
    ingested_at=datetime(2026, 9, 8, tzinfo=UTC),
    membership_snapshot_id="snap-a",
)


def _fact(
    *,
    orders: int | None = 2,
    gmv: Decimal | None = Decimal("10.00"),
    attr: AttributionClass = AttributionClass.DIRECT,
    atc: int | None = 1,
    units: int | None = 3,
    snap: str = "snap-a",
) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=_BASE_KEY,
        metrics=AttributionMetrics(
            attributed_orders=orders,
            attributed_gmv_rub=gmv,
            attributed_atc=atc,
            attributed_units_shks=units,
        ),
        attribution_class=attr,
        provenance=ObservationProvenance(
            observation_id="x",
            source_revision=_PROV.source_revision,
            ingested_at=_PROV.ingested_at,
            membership_snapshot_id=snap,
        ),
    )


def test_identical_semantic_replay_same_id() -> None:
    a = _fact()
    b = _fact()
    assert semantic_observation_id(a) == semantic_observation_id(b)


def test_orders_change_new_id() -> None:
    assert semantic_observation_id(_fact(orders=0)) != semantic_observation_id(_fact(orders=1))


def test_gmv_change_new_id() -> None:
    assert semantic_observation_id(_fact(gmv=Decimal("0"))) != semantic_observation_id(
        _fact(gmv=Decimal("1"))
    )


def test_attribution_class_change_new_id() -> None:
    assert semantic_observation_id(_fact(attr=AttributionClass.DIRECT)) != semantic_observation_id(
        _fact(attr=AttributionClass.LINKED)
    )


def test_membership_snapshot_change_new_id() -> None:
    assert semantic_observation_id(_fact(snap="snap-a")) != semantic_observation_id(
        _fact(snap="snap-b")
    )


def test_atc_change_new_id() -> None:
    assert semantic_observation_id(_fact(atc=0)) != semantic_observation_id(_fact(atc=1))


def test_units_shks_change_new_id() -> None:
    assert semantic_observation_id(_fact(units=1)) != semantic_observation_id(_fact(units=2))


def test_missing_orders_vs_explicit_zero_differ() -> None:
    assert semantic_observation_id(_fact(orders=None)) != semantic_observation_id(
        _fact(orders=0)
    )
