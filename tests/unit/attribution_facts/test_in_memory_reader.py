"""Unit-тесты InMemoryAttributionFactsReader."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    SourceFamily,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionFactKey,
    AttributionMetrics,
    AttributionScope,
    DateWindow,
    DayReconciliationResult,
    ObservationProvenance,
)
from app.modules.attribution_facts.testing.in_memory_reader import (
    InMemoryAttributionFactsReader,
)

pytestmark = pytest.mark.unit

_DAY = date(2026, 9, 7)
_PROV = ObservationProvenance(
    observation_id="o1",
    source_revision=1,
    ingested_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
    membership_snapshot_id="snap",
)


@pytest.mark.asyncio
async def test_in_memory_reader_filters_scope() -> None:
    """Reader возвращает facts только для shop и adv_id."""
    fact = AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="shop-a",
            physical_adv_id=10,
            event_date=_DAY,
            app_type=1,
            ordered_nm_id=1,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(attributed_orders=1, attributed_gmv_rub=Decimal("1")),
        attribution_class=AttributionClass.DIRECT,
        provenance=_PROV,
    )
    recon = DayReconciliationResult(
        physical_adv_id=10,
        event_date=_DAY,
        passed=True,
        nm_orders_sum=1,
        day_orders=1,
        nm_gmv_sum=Decimal("1"),
        day_gmv_rub=Decimal("1"),
        unattributed_orders=0,
    )
    reader = InMemoryAttributionFactsReader(
        facts=(fact,),
        reconciliations=(recon,),
        source_complete_through=_DAY,
    )
    result = await reader.query(
        AttributionScope(shop_id="shop-a", physical_adv_ids=frozenset({10})),
        DateWindow(_DAY, _DAY),
    )
    assert len(result.facts) == 1
    assert result.coverage.status == AttributionCoverageStatus.COMPLETE
