"""Pre-write gate: route epoch и collection ownership перед fact grain.

Spec: ``connected-shop-campaign-ad-data-collection`` (design §C, §D.1, task 4.4).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Единственный durable route epoch — ``shop_campaign_inventory.route_version``.
Availability row несёт тот же ``route_version``, но **не** авторизует запись fact grain.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CampaignRouteDecision,
    CollectionRoute,
)

# Reason codes для availability (design Open Questions — literal String в CH).
REASON_ROUTE_EPOCH_STALE = "route_epoch_stale"
REASON_OWNERSHIP_MISMATCH = "ownership_mismatch"
REASON_COLLECTOR_SOURCE_ERROR = "collector_source_error"
REASON_FACT_WRITE_ERROR = "fact_write_error"
REASON_UNMANAGED_FACT_WRITE_SUCCEEDED = "unmanaged_fact_write_succeeded"
REASON_UNMANAGED_FACT_WRITE_SKIPPED = "unmanaged_fact_write_skipped"
REASON_UNMANAGED_NOT_ELIGIBLE = "unmanaged_not_eligible"
REASON_ROUTE_TRANSITION_RECONCILE = "route_transition_reconcile"

COLLECTOR_UNMANAGED_FULL_ADV = "unmanaged_full_adv_wb_stat"
COLLECTOR_ROUTE_TRANSITION_RECONCILE = "route_transition_reconcile"


@dataclass(frozen=True, slots=True)
class InventoryRouteSnapshot:
    """Текущая строка inventory после argMax — epoch и collection route."""

    adv_id: int
    route: str
    route_version: int


@dataclass(frozen=True, slots=True)
class RouteWriteGateInput:
    """Вход gate непосредственно перед записью fact grain."""

    shop_id: str
    adv_id: int
    observed_route_version: int
    current_inventory: InventoryRouteSnapshot | None
    route_decision: CampaignRouteDecision | None


@dataclass(frozen=True, slots=True)
class RouteWriteGateDecision:
    """Решение gate: разрешена ли запись ``full_adv_wb_stat`` для adv_id."""

    adv_id: int
    allow_fact_write: bool
    reason_code: str
    checked_route_version: int


def evaluate_unmanaged_fact_write_gate(
    gate_input: RouteWriteGateInput,
) -> RouteWriteGateDecision:
    """Сверить epoch и ownership перед unmanaged insert в ``full_adv_wb_stat``.

    Запись разрешена только если:
    - resolver по-прежнему классифицирует ``UNMANAGED`` для ``full_adv_wb_stat``;
    - inventory ``route`` совпадает с ``CollectionRoute.UNMANAGED``;
    - ``route_version`` в inventory равен наблюдённому на старте tick для adv_id.

    Availability с тем же ``route_version`` **не** заменяет этот запрет.

    Args:
        gate_input: снимок epoch на старте tick и актуальный inventory read.

    Returns:
        Решение с ``checked_route_version`` для availability row.
    """
    adv_id = gate_input.adv_id
    decision = gate_input.route_decision
    if decision is None or not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        decision
    ):
        return RouteWriteGateDecision(
            adv_id=adv_id,
            allow_fact_write=False,
            reason_code=REASON_UNMANAGED_NOT_ELIGIBLE,
            checked_route_version=gate_input.observed_route_version,
        )

    current = gate_input.current_inventory
    if current is None:
        return RouteWriteGateDecision(
            adv_id=adv_id,
            allow_fact_write=False,
            reason_code=REASON_OWNERSHIP_MISMATCH,
            checked_route_version=gate_input.observed_route_version,
        )

    checked_version = current.route_version
    if current.route != CollectionRoute.UNMANAGED.value:
        return RouteWriteGateDecision(
            adv_id=adv_id,
            allow_fact_write=False,
            reason_code=REASON_OWNERSHIP_MISMATCH,
            checked_route_version=checked_version,
        )

    if checked_version != gate_input.observed_route_version:
        return RouteWriteGateDecision(
            adv_id=adv_id,
            allow_fact_write=False,
            reason_code=REASON_ROUTE_EPOCH_STALE,
            checked_route_version=checked_version,
        )

    if decision.key.grain is not CampaignCollectionGrain.FULL_ADV_WB_STAT:
        return RouteWriteGateDecision(
            adv_id=adv_id,
            allow_fact_write=False,
            reason_code=REASON_OWNERSHIP_MISMATCH,
            checked_route_version=checked_version,
        )

    return RouteWriteGateDecision(
        adv_id=adv_id,
        allow_fact_write=True,
        reason_code=REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
        checked_route_version=checked_version,
    )
