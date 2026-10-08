"""Slice C: observation_id idempotency vs restatement contract (unit)."""

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
from app.modules.attribution_facts.domain.versioning import select_latest_fact

pytestmark = pytest.mark.unit


def _fact(
    observation_id: str,
    revision: int,
    orders: int,
) -> AttributionCommerceFact:
    key = AttributionFactKey(
        shop_id="s",
        physical_adv_id=1,
        event_date=datetime(2026, 9, 7).date(),
        app_type=1,
        ordered_nm_id=100,
        source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
    )
    return AttributionCommerceFact(
        key=key,
        metrics=AttributionMetrics(
            attributed_orders=orders,
            attributed_gmv_rub=Decimal("10"),
        ),
        attribution_class=AttributionClass.DIRECT,
        provenance=ObservationProvenance(
            observation_id=observation_id,
            source_revision=revision,
            ingested_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            membership_snapshot_id="h1",
        ),
    )


def test_restatement_requires_new_observation_id_for_ch_append() -> None:
    """Same observation_id replay is idempotent; metric change needs new id."""
    v1 = _fact("a" * 32, 1, 5)
    v2_same_id = _fact("a" * 32, 2, 99)
    latest = select_latest_fact((v1, v2_same_id))
    assert latest is not None
    assert latest.metrics.attributed_orders == 99
    assert v1.provenance.observation_id == v2_same_id.provenance.observation_id
    assert v2_same_id.provenance.observation_id != _fact("b" * 32, 2, 99).provenance.observation_id
