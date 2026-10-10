"""DIRECT order value, target CPO и fail-closed кампании."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.runtime.campaign_order_value import (
    campaign_order_value,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionClass,
    AttributionCoverageStatus,
    SourceFamily,
)
from app.modules.attribution_facts.domain.models import (
    AttributionCommerceFact,
    AttributionCoverage,
    AttributionFactKey,
    AttributionMetrics,
    DateWindow,
    ObservationProvenance,
)

pytestmark = pytest.mark.unit

_WINDOW = DateWindow(start=date(2026, 10, 1), end=date(2026, 10, 7))
_PROV = ObservationProvenance(
    observation_id="obs",
    source_revision=1,
    ingested_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
    membership_snapshot_id="snap",
)


def _fact(
    nm_id: int,
    orders: int | None,
    gmv: Decimal | None,
    attr: AttributionClass = AttributionClass.DIRECT,
) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="shop",
            physical_adv_id=10,
            event_date=date(2026, 10, 3),
            app_type=1,
            ordered_nm_id=nm_id,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(attributed_orders=orders, attributed_gmv_rub=gmv),
        attribution_class=attr,
        provenance=_PROV,
    )


def _coverage(
    status: AttributionCoverageStatus = AttributionCoverageStatus.COMPLETE,
) -> AttributionCoverage:
    return AttributionCoverage(
        status=status,
        source_complete_through=_WINDOW.end,
        effective_covered_range_start=_WINDOW.start,
        effective_covered_range_end=_WINDOW.end,
    )


def test_target_cpo_half_up_and_campaign_drr() -> None:
    value = campaign_order_value(
        (_fact(1, 1, Decimal(1200)),),
        _coverage(),
        campaign_spend_rub=Decimal(12000),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert value.reason_codes == ()
    assert value.expected_order_value_rub == Decimal(1200)
    assert value.target_cpo_rub == Decimal("120.00")
    direct = campaign_order_value(
        (_fact(1, 1, Decimal(100_000)),),
        _coverage(),
        campaign_spend_rub=Decimal(12_000),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert direct.campaign_actual_drr_percent == Decimal("12.00")


def test_multi_nm_uses_sums_not_mean_of_ratios() -> None:
    value = campaign_order_value(
        (
            _fact(1, 1, Decimal(100)),
            _fact(2, 2, Decimal(100)),
        ),
        _coverage(),
        campaign_spend_rub=Decimal(30),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert value.direct_orders == 3
    assert value.direct_gmv_rub == Decimal(200)
    assert value.expected_order_value_rub == Decimal(200) / Decimal(3)


def test_linked_rows_do_not_enter_denominator() -> None:
    value = campaign_order_value(
        (
            _fact(1, 1, Decimal(100), AttributionClass.DIRECT),
            _fact(2, 50, Decimal(50_000), AttributionClass.LINKED),
        ),
        _coverage(),
        campaign_spend_rub=Decimal(10),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert value.direct_orders == 1
    assert value.direct_gmv_rub == Decimal(100)
    assert value.target_cpo_rub == Decimal("10.00")


def test_zero_direct_orders_are_unavailable() -> None:
    value = campaign_order_value(
        (_fact(1, 0, Decimal(100)),),
        _coverage(),
        campaign_spend_rub=Decimal(10),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert value.reason_codes == (AdControlReasonCode.ORDER_VALUE_UNAVAILABLE,)
    assert value.target_cpo_rub is None


def test_missing_direct_and_incomplete_window() -> None:
    missing = campaign_order_value(
        (_fact(1, 1, Decimal(10), AttributionClass.LINKED),),
        _coverage(AttributionCoverageStatus.NO_DATA),
        campaign_spend_rub=Decimal(1),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert missing.reason_codes == (AdControlReasonCode.DIRECT_ATTRIBUTION_MISSING,)
    incomplete = campaign_order_value(
        (_fact(1, 1, Decimal(10)),),
        _coverage(AttributionCoverageStatus.PARTIAL),
        campaign_spend_rub=Decimal(1),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert incomplete.reason_codes == (
        AdControlReasonCode.ATTRIBUTION_WINDOW_INCOMPLETE,
    )


def test_null_metric_and_stale_facts() -> None:
    insufficient = campaign_order_value(
        (_fact(1, None, Decimal(10)),),
        _coverage(),
        campaign_spend_rub=Decimal(1),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
    )
    assert insufficient.reason_codes == (
        AdControlReasonCode.DIRECT_ATTRIBUTION_INSUFFICIENT,
    )
    stale = campaign_order_value(
        (_fact(1, 1, Decimal(10)),),
        _coverage(),
        campaign_spend_rub=Decimal(1),
        effective_target_drr_percent=Decimal(10),
        window=_WINDOW,
        facts_stale=True,
    )
    assert stale.reason_codes == (AdControlReasonCode.ATTRIBUTION_FACT_STALE,)
    assert stale.target_cpo_rub is None
