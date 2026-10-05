"""Handoff UNMANAGED ↔ MANAGED: non-atomic collection ownership (design §C, §7.1–§7.4).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Чистый domain-seam для connect/disconnect transitions без wiring в
``WBShop.run``. Симулирует последовательные resolver ticks до/после
``connect_existing_advs`` commit или terminal ``done``. Management
relationship **не** доказывается routing layer (§B.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CollectionRoute,
    RouteResolverTickInput,
    RouteResolverTickResult,
)


@dataclass(frozen=True, slots=True)
class ConnectHandoffTickResult:
    """S16: два resolver tick вокруг user connect enrollment commit."""

    shop_id: str
    connect_adv_ids: frozenset[int]
    tick_before_connect: RouteResolverTickResult
    tick_after_connect: RouteResolverTickResult


@dataclass(frozen=True, slots=True)
class DoneDisconnectHandoffResult:
    """S18: resolver ticks до/после terminal ``done`` enrollment."""

    shop_id: str
    done_adv_ids: frozenset[int]
    tick_before_done: RouteResolverTickResult
    tick_after_done: RouteResolverTickResult


@dataclass(frozen=True, slots=True)
class RefusedOwnershipStabilityResult:
    """S19: refused enrollment остаёт на managed ownership."""

    shop_id: str
    refused_adv_ids: frozenset[int]
    tick_result: RouteResolverTickResult
    all_remain_managed: bool


def resolve_connect_handoff_next_tick(
    *,
    shop_id: str,
    wb_discovered_adv_ids: frozenset[int],
    loader_before_connect: Sequence[ComplexAdv],
    loader_after_connect: Sequence[ComplexAdv],
    connect_adv_ids: frozenset[int],
) -> ConnectHandoffTickResult:
    """S16: post-connect tick — MANAGED collection для затронутых adv_id.

    Моделирует enrollment commit ``connect_existing_advs``: loader после commit
    включает upserted ``AdvSetting`` с ``active_status != 'done'``.

    Args:
        shop_id: магазин shop-runner.
        wb_discovered_adv_ids: WB discovery snapshot (union до/после connect).
        loader_before_connect: ``get_complex_advs(only_bot_active=False)`` до connect.
        loader_after_connect: loader после commit connect.
        connect_adv_ids: physical ids, подключённые пользователем.

    Returns:
        Пара resolver results; ``tick_after_connect`` — authoritative next tick.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    resolver = CampaignCollectionRouteResolver()
    before = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=wb_discovered_adv_ids,
            loader_complex_advs=tuple(loader_before_connect),
        )
    )
    after = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=wb_discovered_adv_ids,
            loader_complex_advs=tuple(loader_after_connect),
        )
    )
    return ConnectHandoffTickResult(
        shop_id=shop_id,
        connect_adv_ids=connect_adv_ids,
        tick_before_connect=before,
        tick_after_connect=after,
    )


def connect_handoff_newly_managed_adv_ids(
    result: ConnectHandoffTickResult,
) -> frozenset[int]:
    """Adv ids, перешедшие UNMANAGED → MANAGED collection ownership (S16)."""
    before_routes = result.tick_before_connect.routes_by_grain(
        CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    after_routes = result.tick_after_connect.routes_by_grain(
        CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    newly_managed: set[int] = set()
    for adv_id in result.connect_adv_ids:
        if (
            before_routes.get(adv_id) is CollectionRoute.UNMANAGED
            and after_routes.get(adv_id) is CollectionRoute.MANAGED
        ):
            newly_managed.add(adv_id)
    return frozenset(newly_managed)


def unmanaged_blocked_adv_ids_after_connect(
    result: ConnectHandoffTickResult,
) -> frozenset[int]:
    """После connect tick unmanaged MUST NOT писать owned grains (S16)."""
    blocked: set[int] = set()
    for adv_id in result.connect_adv_ids:
        decision = result.tick_after_connect.decision_for(
            adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT
        )
        if decision is None:
            continue
        if not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
            decision
        ):
            blocked.add(adv_id)
    return frozenset(blocked)


def resolve_done_disconnect_handoff(
    *,
    shop_id: str,
    wb_discovered_adv_ids: frozenset[int],
    loader_before_done: Sequence[ComplexAdv],
    loader_after_done: Sequence[ComplexAdv],
    done_adv_ids: frozenset[int],
) -> DoneDisconnectHandoffResult:
    """S18: ``active_status`` → ``done`` — managed RECORD прекращается, UNMANAGED resume.

    Args:
        shop_id: магазин shop-runner.
        wb_discovered_adv_ids: WB discovery (кампания всё ещё видна в WB).
        loader_before_done: loader до terminal done.
        loader_after_done: loader после done (строка выпала из ``__get_advs``).
        done_adv_ids: adv_ids, переведённые в terminal done.

    Returns:
        Пара resolver ticks; ``tick_after_done`` — authoritative next tick.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    resolver = CampaignCollectionRouteResolver()
    before = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=wb_discovered_adv_ids,
            loader_complex_advs=tuple(loader_before_done),
        )
    )
    after = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=wb_discovered_adv_ids,
            loader_complex_advs=tuple(loader_after_done),
        )
    )
    return DoneDisconnectHandoffResult(
        shop_id=shop_id,
        done_adv_ids=done_adv_ids,
        tick_before_done=before,
        tick_after_done=after,
    )


def done_handoff_transitioned_to_unmanaged(
    result: DoneDisconnectHandoffResult,
) -> frozenset[int]:
    """Adv ids, перешедшие MANAGED → UNMANAGED после terminal done (S18)."""
    before_routes = result.tick_before_done.routes_by_grain(
        CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    after_routes = result.tick_after_done.routes_by_grain(
        CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    transitioned: set[int] = set()
    for adv_id in result.done_adv_ids:
        if (
            before_routes.get(adv_id) is CollectionRoute.MANAGED
            and after_routes.get(adv_id) is CollectionRoute.UNMANAGED
        ):
            transitioned.add(adv_id)
    return frozenset(transitioned)


def evaluate_refused_disconnect_like_handoff(
    *,
    shop_id: str,
    wb_discovered_adv_ids: frozenset[int],
    loader_with_refused: Sequence[ComplexAdv],
) -> RefusedOwnershipStabilityResult:
    """S19: ``refused`` MUST NOT переводить ownership на unmanaged alone.

    Disconnect-like UI predicate исключает ``refused``, но loader §B.1
    **включает** ``refused`` в managed RECORD universe.

    Args:
        shop_id: магазин shop-runner.
        wb_discovered_adv_ids: WB discovery snapshot.
        loader_with_refused: loader с ``active_status='refused'``.

    Returns:
        Стабильность managed ownership для всех refused adv ids.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    tick_result = CampaignCollectionRouteResolver().resolve_tick(
        RouteResolverTickInput(
            shop_id=shop_id,
            wb_discovered_adv_ids=wb_discovered_adv_ids,
            loader_complex_advs=tuple(loader_with_refused),
        )
    )
    refused_ids = tick_result.managed_ownership_adv_ids
    all_managed = True
    for adv_id in refused_ids:
        decision = tick_result.decision_for(
            adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT
        )
        if decision is None or decision.route is not CollectionRoute.MANAGED:
            all_managed = False
            break
        if CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
            decision
        ):
            all_managed = False
            break
    return RefusedOwnershipStabilityResult(
        shop_id=shop_id,
        refused_adv_ids=refused_ids,
        tick_result=tick_result,
        all_remain_managed=all_managed,
    )
