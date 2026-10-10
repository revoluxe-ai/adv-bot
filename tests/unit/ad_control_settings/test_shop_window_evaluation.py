"""Shop-window orchestration: один supplier-orders сбор и order-value proposal."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.diagnostics_builder import (
    AdControlDiagnosticsBuilder,
)
from app.modules.ad_control_settings.domain.drr_state import ActualDrrObservation
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    DataSufficiency,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverContext,
    ShopFeatureSlot,
)
from app.modules.ad_control_settings.runtime.evaluation import (
    ShopEvaluationRequest,
    evaluate_shop_window,
    select_campaign_ids,
)
from app.modules.ad_control_settings.runtime.shop_order_gmv import MOSCOW
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
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
    ObservationProvenance,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent

pytestmark = pytest.mark.unit

_WINDOW = DateWindow(start=date(2026, 10, 1), end=date(2026, 10, 7))
_NOW = datetime(2026, 10, 8, 4, tzinfo=MOSCOW)


def _context(
    advert_id: int,
    *,
    mode: AdControlFeatureMode = AdControlFeatureMode.INHERIT,
    shop_target: int = 8,
    enrolled: HierarchicalEnrollment = HierarchicalEnrollment.ENROLLED,
    campaign_target: int | None = None,
) -> ResolverContext:
    payload = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(shop_target), Decimal(shop_target + 5)),
    )
    campaign_payload = None
    if campaign_target is not None:
        campaign_payload = DrrPolicyParamsV1(
            profile=drr_profile_from_percent(
                Decimal(campaign_target),
                Decimal(campaign_target + 5),
            ),
        )
    return ResolverContext(
        enrollment=enrolled,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="shop",
        shop_features={
            AdControlFeatureId.DRR_POLICY: ShopFeatureSlot(
                activation=ShopFeatureActivation.ENABLED,
                payload=payload,
            ),
        },
        campaign=CampaignRef(shop_id="shop", advert_id=advert_id),
        campaign_features={
            AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                mode=mode,
                payload=campaign_payload,
            ),
        },
    )


def _fact(adv_id: int, nm_id: int, orders: int, gmv: Decimal) -> AttributionCommerceFact:
    return AttributionCommerceFact(
        key=AttributionFactKey(
            shop_id="shop",
            physical_adv_id=adv_id,
            event_date=date(2026, 10, 3),
            app_type=1,
            ordered_nm_id=nm_id,
            source_family=SourceFamily.WB_PROMOTION_FULLSTATS_NM_DAY,
        ),
        metrics=AttributionMetrics(attributed_orders=orders, attributed_gmv_rub=gmv),
        attribution_class=AttributionClass.DIRECT,
        provenance=ObservationProvenance(
            observation_id=f"{adv_id}-{nm_id}",
            source_revision=1,
            ingested_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
            membership_snapshot_id="snap",
        ),
    )


def _query(facts: tuple[AttributionCommerceFact, ...]) -> AttributionQueryResult:
    return AttributionQueryResult(
        facts=facts,
        coverage=AttributionCoverage(
            status=AttributionCoverageStatus.COMPLETE,
            source_complete_through=_WINDOW.end,
            effective_covered_range_end=_WINDOW.end,
        ),
    )


class _Orders:
    def __init__(self, pages: list[list[dict[str, object]]]) -> None:
        self.pages = pages
        self.calls = 0

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int = 0,
    ) -> list[dict[str, object]]:
        self.calls += 1
        if not self.pages:
            return []
        return self.pages.pop(0)


class _Spend:
    def __init__(self, rows: dict[int, Decimal]) -> None:
        self.rows = rows
        self.calls = 0

    async def sum_spend_by_adv(
        self,
        adv_ids: tuple[int, ...],
        window: DateWindow,
    ) -> dict[int, Decimal]:
        self.calls += 1
        assert window == _WINDOW
        return self.rows


class _Facts:
    def __init__(self, by_adv: dict[int, AttributionQueryResult]) -> None:
        self.by_adv = by_adv
        self.scopes: list[frozenset[int]] = []

    async def query(
        self,
        scope: AttributionScope,
        window: DateWindow,
    ) -> AttributionQueryResult:
        assert window == _WINDOW
        self.scopes.append(scope.physical_adv_ids)
        adv_id = next(iter(scope.physical_adv_ids))
        return self.by_adv[adv_id]


def _order_row(price: int = 1_000_000) -> dict[str, object]:
    return {
        "srid": "row-1",
        "priceWithDisc": price,
        "isCancel": False,
        "date": "2026-10-04T08:00:00",
        "lastChangeDate": "2026-10-04T09:00:00",
        "gNumber": "cart-1",
    }


@pytest.mark.asyncio
async def test_one_supplier_read_for_two_campaigns_and_order_value_proposal() -> None:
    orders = _Orders([[_order_row()], []])
    spend = _Spend({11: Decimal(40_000), 12: Decimal(50_000)})
    facts = _Facts(
        {
            11: _query((_fact(11, 1, 1, Decimal(100_000)),)),
            12: _query((_fact(12, 2, 2, Decimal(200_000)),)),
        }
    )
    result = await evaluate_shop_window(
        ShopEvaluationRequest(
            shop_id="shop",
            window=_WINDOW,
            collected_at=_NOW,
            enrolled=True,
            contexts=(_context(11), _context(12)),
            inventory_adv_ids=(11, 12),
            shop_target_drr_percent=Decimal(8),
        ),
        orders=orders,
        spend=spend,
        attribution=facts,
    )
    assert result.supplier_order_collections == 1
    assert orders.calls == 2
    assert spend.calls == 1
    assert facts.scopes == [frozenset({11}), frozenset({12})]
    assert result.shop is not None
    assert result.shop.headroom_rub == Decimal(-10_000)
    assert result.shop.actual_drr_percent == Decimal("9.00")
    assert len(result.reports) == 2
    first = result.reports[0]
    assert first.proposed_cpo is not None
    assert first.proposed_cpo.proposed_max_cpo_rub == Decimal("8000.00")
    assert first.proposed_cpo.decision == "DIAGNOSTIC_ORDER_VALUE_TARGET_CPO"
    assert (
        AdControlReasonCode.HEADROOM_ALLOCATOR_NOT_ACCEPTED
        in first.proposed_cpo.reason_codes
    )
    assert (
        AdControlReasonCode.PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED
        not in first.reason_codes
    )


@pytest.mark.asyncio
async def test_not_enrolled_and_foreign_basis_do_not_read_orders() -> None:
    orders = _Orders([[_order_row()]])

    async def _fail_spend(
        adv_ids: tuple[int, ...],
        window: DateWindow,
    ) -> dict[int, Decimal]:
        raise AssertionError("spend")

    class _BoomFacts:
        async def query(
            self,
            scope: AttributionScope,
            window: DateWindow,
        ) -> AttributionQueryResult:
            raise AssertionError("facts")

    not_enrolled = await evaluate_shop_window(
        ShopEvaluationRequest(
            shop_id="shop",
            window=_WINDOW,
            collected_at=_NOW,
            enrolled=False,
            contexts=(_context(11, enrolled=HierarchicalEnrollment.NOT_ENROLLED),),
        ),
        orders=orders,
        spend=_Spend({}),
        attribution=_BoomFacts(),
    )
    assert not_enrolled.supplier_order_collections == 0
    assert orders.calls == 0
    assert not_enrolled.reason_codes == (
        AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED,
    )
    foreign = await evaluate_shop_window(
        ShopEvaluationRequest(
            shop_id="shop",
            window=_WINDOW,
            collected_at=_NOW,
            enrolled=True,
            revenue_basis="BUYOUT_GMV",
            contexts=(_context(11),),
        ),
        orders=orders,
        spend=_Spend({}),
        attribution=_BoomFacts(),
    )
    assert foreign.supplier_order_collections == 0
    assert orders.calls == 0
    assert foreign.reason_codes == (AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED,)


@pytest.mark.asyncio
async def test_campaign_override_target_and_disabled_campaign() -> None:
    orders = _Orders([[_order_row()], []])
    spend = _Spend({11: Decimal(90_000)})
    facts = _Facts({11: _query((_fact(11, 1, 1, Decimal(1_000)),))})
    override = await evaluate_shop_window(
        ShopEvaluationRequest(
            shop_id="shop",
            window=_WINDOW,
            collected_at=_NOW,
            enrolled=True,
            contexts=(
                _context(
                    11,
                    mode=AdControlFeatureMode.OVERRIDE,
                    shop_target=15,
                    campaign_target=8,
                ),
            ),
            inventory_adv_ids=(11,),
            shop_target_drr_percent=Decimal(15),
        ),
        orders=orders,
        spend=spend,
        attribution=facts,
    )
    report = override.reports[0]
    assert report.shop_headroom is not None
    assert report.shop_headroom.configured_target_drr_percent == Decimal(15)
    assert report.shop_headroom.headroom_rub == Decimal(60_000)
    assert override.shop is not None
    assert override.shop.allowed_spend_rub == Decimal(150_000)
    assert report.proposed_cpo is not None
    assert report.proposed_cpo.proposed_max_cpo_rub == Decimal("80.00")

    orders_disabled = _Orders([[_order_row()], []])
    disabled = await evaluate_shop_window(
        ShopEvaluationRequest(
            shop_id="shop",
            window=_WINDOW,
            collected_at=_NOW,
            enrolled=True,
            contexts=(_context(11, mode=AdControlFeatureMode.DISABLED),),
            inventory_adv_ids=(11,),
            shop_target_drr_percent=Decimal(8),
        ),
        orders=orders_disabled,
        spend=_Spend({11: Decimal(1)}),
        attribution=_Facts({11: _query((_fact(11, 1, 1, Decimal(100)),))}),
    )
    assert disabled.supplier_order_collections == 1
    assert disabled.reports[0].proposed_cpo is None
    assert (
        AdControlReasonCode.FEATURE_DISABLED_AT_CAMPAIGN
        in disabled.reports[0].reason_codes
    )


def test_history_then_inventory_campaign_ids() -> None:
    assert select_campaign_ids((1, 2), (9,)) == (1, 2)
    assert select_campaign_ids((), (9,)) == (9,)
    assert select_campaign_ids(None, (4,)) == (4,)
    assert select_campaign_ids(None, None) == ()


def test_catalog_path_stays_blocked_without_order_value() -> None:
    actual = ActualDrrObservation(
        actual_drr_percent=Decimal(9),
        measurement_window_id="2026-10-01/2026-10-07",
        data_sufficiency=DataSufficiency.SUFFICIENT,
        attribution_lag_days=None,
    )
    report = AdControlDiagnosticsBuilder.build(_context(11), actual)
    assert report.proposed_cpo is not None
    assert (
        AdControlReasonCode.PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED
        in report.proposed_cpo.reason_codes
    )
    assert report.proposed_cpo.proposed_max_cpo_rub is None
