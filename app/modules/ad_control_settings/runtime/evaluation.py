"""
Одна оценка магазина за окно: один supplier-orders read и diagnostics.

Кампании читают только ``AttributionFactsReader``. Allocator и Apply не вызываются.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.diagnostics import (
    AdControlDiagnosticsReportV1,
)
from app.modules.ad_control_settings.domain.diagnostics_builder import (
    AdControlDiagnosticsBuilder,
)
from app.modules.ad_control_settings.domain.drr_state import ActualDrrObservation
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    DataSufficiency,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.domain.resolver import AdControlSettingsResolver
from app.modules.ad_control_settings.domain.resolver_models import (
    ResolverBlocked,
    ResolverContext,
)
from app.modules.ad_control_settings.runtime.campaign_order_value import (
    campaign_order_value,
)
from app.modules.ad_control_settings.runtime.ports import (
    AttributionQueryPort,
    ShopSpendPort,
    SupplierOrdersPagePort,
)
from app.modules.ad_control_settings.runtime.shop_factual import (
    ShopFactualEconomics,
    shop_factual_economics,
)
from app.modules.ad_control_settings.runtime.shop_order_gmv import (
    ShopOrderGmvAggregate,
    V1_REVENUE_BASIS,
    aggregate_shop_order_gmv,
    window_id,
)
from app.modules.ad_control_settings.runtime.supplier_orders_collect import (
    DEFAULT_API_BUDGET,
    DEFAULT_MAX_PAGES,
    collect_supplier_orders,
)
from app.modules.attribution_facts.domain.models import AttributionScope, DateWindow


@dataclass(frozen=True, slots=True)
class ShopEvaluationRequest:
    """Вход одной shop-level оценки. Supplier orders не зависят от кампании."""

    shop_id: str
    window: DateWindow
    collected_at: datetime
    enrolled: bool
    contexts: tuple[ResolverContext, ...] = ()
    revenue_basis: str = V1_REVENUE_BASIS
    inventory_adv_ids: tuple[int, ...] | None = None
    shop_target_drr_percent: Decimal | None = None
    facts_stale: bool = False
    max_pages: int = DEFAULT_MAX_PAGES
    api_budget: int = DEFAULT_API_BUDGET


@dataclass(frozen=True, slots=True)
class ShopEvaluationResult:
    """Диагностики кампаний и учёт единственного supplier-orders сбора."""

    reports: tuple[AdControlDiagnosticsReportV1, ...]
    gmv: ShopOrderGmvAggregate | None
    shop: ShopFactualEconomics | None
    supplier_order_collections: int
    reason_codes: tuple[AdControlReasonCode, ...]


async def evaluate_shop_window(
    request: ShopEvaluationRequest,
    *,
    orders: SupplierOrdersPagePort,
    spend: ShopSpendPort,
    attribution: AttributionQueryPort,
) -> ShopEvaluationResult:
    """
    Посчитать read-only diagnostics.

    При ``enrolled=False`` или чужом revenue basis порт заказов не вызывается.
    Успешный путь собирает supplier orders ровно один раз на этот вызов.
    """
    if not request.enrolled:
        reports = tuple(
            AdControlDiagnosticsBuilder.build(context, None)
            for context in request.contexts
        )
        return ShopEvaluationResult(
            reports=reports,
            gmv=None,
            shop=None,
            supplier_order_collections=0,
            reason_codes=(AdControlReasonCode.NOT_ENROLLED_FAIL_CLOSED,),
        )
    if request.revenue_basis != V1_REVENUE_BASIS:
        return ShopEvaluationResult(
            reports=_reports_without_facts(request.contexts),
            gmv=None,
            shop=None,
            supplier_order_collections=0,
            reason_codes=(AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED,),
        )

    collected = await collect_supplier_orders(
        orders,
        window=request.window,
        collected_at=request.collected_at,
        max_pages=request.max_pages,
        api_budget=request.api_budget,
    )
    gmv = aggregate_shop_order_gmv(
        collected.lines,
        request.window,
        collected.verdict,
        revenue_basis=request.revenue_basis,
    )
    spend_map: dict[int, Decimal] | None
    if request.inventory_adv_ids is None:
        spend_map = None
    elif not request.inventory_adv_ids:
        spend_map = {}
    else:
        spend_map = await spend.sum_spend_by_adv(
            request.inventory_adv_ids,
            request.window,
        )
    spend_rub = None if spend_map is None else sum(spend_map.values(), Decimal(0))
    spend_window = None if spend_map is None else request.window
    shop_target = request.shop_target_drr_percent
    if shop_target is None and request.contexts:
        shop_target = _shop_target(request.contexts[0])
    shop = shop_factual_economics(
        gmv,
        spend_rub=spend_rub,
        spend_window=spend_window,
        shop_target_drr_percent=shop_target,
    )
    inventory_set = (
        set(request.inventory_adv_ids)
        if request.inventory_adv_ids is not None
        else set()
    )
    reports: list[AdControlDiagnosticsReportV1] = []
    for context in request.contexts:
        if context.shop_id != request.shop_id:
            raise ValueError("campaign context shop_id must match the evaluation shop")
        campaign_spend = _campaign_spend(
            context.campaign.advert_id,
            spend_map,
            inventory_set,
            inventory_known=request.inventory_adv_ids is not None,
        )
        scope = AttributionScope(
            shop_id=request.shop_id,
            physical_adv_ids=frozenset({context.campaign.advert_id}),
        )
        queried = await attribution.query(scope, request.window)
        order_value = campaign_order_value(
            queried.facts,
            queried.coverage,
            campaign_spend_rub=campaign_spend,
            effective_target_drr_percent=_effective_target(context),
            window=request.window,
            facts_stale=request.facts_stale,
        )
        report = _report_for_campaign(
            context,
            shop,
            window=request.window,
            order_value_reasons=order_value.reason_codes,
            target_cpo=order_value.target_cpo_rub,
            campaign_actual_percent=order_value.campaign_actual_drr_percent,
            shop_target=shop_target,
        )
        reports.append(report)
    reasons = tuple(dict.fromkeys((*shop.reason_codes,)))
    return ShopEvaluationResult(
        reports=tuple(reports),
        gmv=gmv,
        shop=shop,
        supplier_order_collections=1,
        reason_codes=reasons,
    )


def select_campaign_ids(
    history_ids: tuple[int, ...] | None,
    inventory_ids: tuple[int, ...] | None,
) -> tuple[int, ...]:
    """
    Кампании оценки: непустая settings history, иначе shop_campaign_inventory.

    Spend по-прежнему считается по inventory, не по history.
    """
    if history_ids:
        return history_ids
    if inventory_ids:
        return inventory_ids
    return ()


def _reports_without_facts(
    contexts: tuple[ResolverContext, ...],
) -> tuple[AdControlDiagnosticsReportV1, ...]:
    return tuple(AdControlDiagnosticsBuilder.build(context, None) for context in contexts)


def _shop_target(context: ResolverContext) -> Decimal | None:
    slot = context.shop_features.get(AdControlFeatureId.DRR_POLICY)
    if slot is None or slot.activation != ShopFeatureActivation.ENABLED:
        return None
    if not isinstance(slot.payload, DrrPolicyParamsV1):
        return None
    return slot.payload.profile.target_drr_percent


def _effective_target(context: ResolverContext) -> Decimal | None:
    resolved = AdControlSettingsResolver.resolve_feature(
        context,
        AdControlFeatureId.DRR_POLICY,
    )
    if isinstance(resolved, ResolverBlocked) or not resolved.active:
        return None
    if not isinstance(resolved.payload, DrrPolicyParamsV1):
        return None
    return resolved.payload.profile.target_drr_percent


def _campaign_spend(
    advert_id: int,
    spend_map: dict[int, Decimal] | None,
    inventory_ids: set[int],
    *,
    inventory_known: bool,
) -> Decimal | None:
    if spend_map is None or not inventory_known:
        return None
    if advert_id not in inventory_ids and advert_id not in spend_map:
        return None
    return spend_map.get(advert_id, Decimal(0))


def _report_for_campaign(
    context: ResolverContext,
    shop: ShopFactualEconomics,
    *,
    window: DateWindow,
    order_value_reasons: tuple[AdControlReasonCode, ...],
    target_cpo: Decimal | None,
    campaign_actual_percent: Decimal | None,
    shop_target: Decimal | None,
) -> AdControlDiagnosticsReportV1:
    actual = ActualDrrObservation(
        actual_drr_percent=shop.actual_drr_percent,
        measurement_window_id=window_id(window),
        data_sufficiency=shop.sufficiency,
        attribution_lag_days=None,
    )
    campaign_observed: ActualDrrObservation | None = None
    if campaign_actual_percent is not None and not order_value_reasons:
        campaign_observed = ActualDrrObservation(
            actual_drr_percent=campaign_actual_percent,
            measurement_window_id=window_id(window),
            data_sufficiency=DataSufficiency.SUFFICIENT,
            attribution_lag_days=None,
        )
    blocked_shop = shop.sufficiency != DataSufficiency.SUFFICIENT
    proposal_target = None if blocked_shop else target_cpo
    proposal_reasons = order_value_reasons
    if blocked_shop:
        proposal_reasons = tuple(dict.fromkeys((*shop.reason_codes, *order_value_reasons)))
        proposal_target = None
    return AdControlDiagnosticsBuilder.build(
        context,
        actual,
        allowed_spend_rub=shop.allowed_spend_rub,
        spend_rub=shop.spend_rub,
        v1_order_value=True,
        order_value_target_cpo_rub=proposal_target,
        order_value_reason_codes=proposal_reasons,
        campaign_observed_drr=campaign_observed,
        shop_headroom_target_percent=shop_target,
    )
