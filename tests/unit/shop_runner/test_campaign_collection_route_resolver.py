"""CampaignCollectionRouteResolver — задачи 3.1–3.9, design §B.1 routing table.

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Проверяет чистый resolver без wiring в ``WBShop``/``CoroutinesManager``.
Predicate loader'а не подменяется: вход — post-filter ``ComplexAdv`` и WB discovery.
Секции ``test_task_3*`` — targeted regression evidence для tasks 3.2–3.9 (S02–S21).
"""

from __future__ import annotations

import ast
import importlib
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Mapped

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    REASON_MANAGED_LOADER_OWNERSHIP,
    REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED,
    REASON_UNKNOWN_NOT_CLASSIFIED,
    REASON_UNMANAGED_WB_DISCOVERY,
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CollectionRoute,
    RouteResolverTickInput,
    build_managed_ownership_adv_ids,
)

_SHOP_ID = "shop-route-resolver"
_PARENT_ADV_ID = 101
_SEARCH_ADV_ID = 202
_WB_ONLY_ADV_ID = 999_001
_DONE_ADV_ID = 303


def _setting(
    *,
    adv_id: int,
    nmids: list[int],
    active_status: str,
    bot_active: bool,
    setting_id: int,
) -> MagicMock:
    """Минимальная форма AdvSetting для ComplexAdv без живой PG."""
    row = MagicMock(spec=AdvSetting)
    row.adv_id = adv_id
    row.id = setting_id
    row.nmids = list(nmids)
    row.active_status = active_status
    row.bot_active = bot_active
    row.search_adv_id = None
    row.plan_for_sales_for_day = None
    row.target_price_for_order = None
    row.max_price_for_order = None
    return row


def _refused_parent_with_search(*, bot_active: bool = False) -> ComplexAdv:
    """Refused parent + search leg — типичный §B.1 loader universe."""
    parent = _setting(
        adv_id=_PARENT_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=bot_active,
        setting_id=1,
    )
    search = _setting(
        adv_id=_SEARCH_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=bot_active,
        setting_id=2,
    )
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=parent,
        search_adv=search,
        target_pay_for_order=None,
    )


def _started_parent_only(*, bot_active: bool = False) -> ComplexAdv:
    """Sync-created loader row без search leg."""
    parent = _setting(
        adv_id=_PARENT_ADV_ID,
        nmids=[777],
        active_status="started",
        bot_active=bot_active,
        setting_id=3,
    )
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=parent,
        search_adv=None,
        target_pay_for_order=None,
    )


@pytest.mark.unit
def test_build_managed_ownership_includes_search_legs() -> None:
    """``all_adv_ids`` parent+search входят в ownership set §B.1."""
    loader_adv = _refused_parent_with_search()
    owned = build_managed_ownership_adv_ids([loader_adv])

    assert owned == {_PARENT_ADV_ID, _SEARCH_ADV_ID}


@pytest.mark.unit
def test_wb_only_id_unmanaged_for_full_adv_not_clusters() -> None:
    """S02 predicate: WB-only id → UNMANAGED ``full_adv_wb_stat``, clusters UNKNOWN."""
    resolver = CampaignCollectionRouteResolver()
    discovered = frozenset({_WB_ONLY_ADV_ID})
    managed = frozenset({_PARENT_ADV_ID, _SEARCH_ADV_ID})

    full_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=managed,
    )
    clusters_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.CLUSTERS_ADV_STATS,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=managed,
    )

    assert full_decision.route is CollectionRoute.UNMANAGED
    assert full_decision.reason_code == REASON_UNMANAGED_WB_DISCOVERY
    assert clusters_decision.route is CollectionRoute.UNKNOWN
    assert clusters_decision.reason_code == REASON_UNKNOWN_CLUSTERS_OUTSIDE_MANAGED


@pytest.mark.unit
def test_refused_loader_universe_managed_for_both_grains() -> None:
    """S05: ``refused`` в loader → MANAGED для full_adv и clusters (обе ноги)."""
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_PARENT_ADV_ID, _SEARCH_ADV_ID},
        loader_complex_advs=[_refused_parent_with_search()],
    )

    for adv_id in (_PARENT_ADV_ID, _SEARCH_ADV_ID):
        full = result.decision_for(adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT)
        clusters = result.decision_for(adv_id, CampaignCollectionGrain.CLUSTERS_ADV_STATS)
        assert full is not None
        assert clusters is not None
        assert full.route is CollectionRoute.MANAGED
        assert clusters.route is CollectionRoute.MANAGED
        assert full.reason_code == REASON_MANAGED_LOADER_OWNERSHIP


@pytest.mark.unit
def test_done_enrollment_absent_from_loader_unmanaged_when_discovered() -> None:
    """S06/S07: ``done`` не в loader → UNMANAGED при WB discovery."""
    resolver = CampaignCollectionRouteResolver()
    discovered = frozenset({_DONE_ADV_ID})

    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_DONE_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )

    assert decision.route is CollectionRoute.UNMANAGED
    assert decision.reason_code == REASON_UNMANAGED_WB_DISCOVERY


@pytest.mark.unit
def test_sync_created_loader_row_managed_despite_bot_active_false() -> None:
    """S04: sync row в loader → MANAGED; ``bot_active=False`` не gate ownership."""
    loader_adv = _started_parent_only(bot_active=False)
    assert loader_adv.bot_active is False

    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_PARENT_ADV_ID},
        loader_complex_advs=[loader_adv],
    )
    decision = result.decision_for(_PARENT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)

    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED


@pytest.mark.unit
def test_search_leg_managed_when_parent_in_loader() -> None:
    """S08: search leg через ``all_adv_ids`` → MANAGED ``full_adv_wb_stat``."""
    loader_adv = _refused_parent_with_search()
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_SEARCH_ADV_ID},
        loader_complex_advs=[loader_adv],
    )

    decision = result.decision_for(_SEARCH_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)
    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED


@pytest.mark.unit
def test_neither_managed_nor_discovered_resolves_unknown_fail_closed() -> None:
    """Ambiguous id вне discovery и loader → UNKNOWN (fail-closed)."""
    resolver = CampaignCollectionRouteResolver()
    orphan_id = 404_404

    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=orphan_id,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=frozenset(),
        managed_ownership_adv_ids=frozenset(),
    )

    assert decision.route is CollectionRoute.UNKNOWN
    assert decision.reason_code == REASON_UNKNOWN_NOT_CLASSIFIED


@pytest.mark.unit
def test_clusters_never_unmanaged_even_when_wb_discovered() -> None:
    """``clusters_adv_stats`` never UNMANAGED — только MANAGED или UNKNOWN."""
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_WB_ONLY_ADV_ID, _DONE_ADV_ID},
        loader_complex_advs=[],
    )
    routes = result.routes_by_grain(CampaignCollectionGrain.CLUSTERS_ADV_STATS)

    assert set(routes) == {_WB_ONLY_ADV_ID, _DONE_ADV_ID}
    assert all(route is CollectionRoute.UNKNOWN for route in routes.values())
    assert CollectionRoute.UNMANAGED not in routes.values()


@pytest.mark.unit
def test_resolve_tick_covers_union_managed_and_discovered() -> None:
    """Tick строит решения для union managed ∪ discovered ids × grains."""
    loader_adv = _refused_parent_with_search()
    tick_input = RouteResolverTickInput(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=frozenset({_WB_ONLY_ADV_ID, _PARENT_ADV_ID}),
        loader_complex_advs=(loader_adv,),
    )
    result = CampaignCollectionRouteResolver().resolve_tick(tick_input)

    assert result.managed_ownership_adv_ids == {_PARENT_ADV_ID, _SEARCH_ADV_ID}
    assert len(result.decisions) == 3 * len(CampaignCollectionGrain)
    full_routes = result.routes_by_grain(CampaignCollectionGrain.FULL_ADV_WB_STAT)
    assert full_routes[_PARENT_ADV_ID] is CollectionRoute.MANAGED
    assert full_routes[_SEARCH_ADV_ID] is CollectionRoute.MANAGED
    assert full_routes[_WB_ONLY_ADV_ID] is CollectionRoute.UNMANAGED


@pytest.mark.unit
def test_managed_id_without_wb_discovery_still_managed() -> None:
    """Loader ownership не требует присутствия id в WB discovery snapshot."""
    loader_adv = _started_parent_only()
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=set(),
        loader_complex_advs=[loader_adv],
    )

    decision = result.decision_for(_PARENT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)
    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED


# --- Tasks 3.2–3.9: targeted routing regression evidence (S02–S21) ---


@pytest.mark.unit
def test_task_32_s02_wb_only_unmanaged_no_adv_setting_side_effect() -> None:
    """3.2 / S02: WB-only id → UNMANAGED ``full_adv_wb_stat``; resolver без AdvSetting."""
    resolver = CampaignCollectionRouteResolver()
    discovered = frozenset({_WB_ONLY_ADV_ID})
    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )

    assert decision.route is CollectionRoute.UNMANAGED
    assert decision.reason_code == REASON_UNMANAGED_WB_DISCOVERY
    assert CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        decision
    )
    assert not CampaignCollectionRouteResolver.is_managed_collector_write_eligible(
        decision
    )

    route_module = importlib.import_module(
        "app.modules.shop_runner.shop_wide_collection.route_resolver"
    )
    assert "AdvSetting" not in route_module.__dict__
    tree = ast.parse(inspect.getsource(route_module))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "AdvSetting" not in imported_names


@pytest.mark.unit
def test_task_33_s04_sync_row_managed_management_unproven() -> None:
    """3.3 / S04: sync-created loader row → MANAGED collection; connect unproven."""
    loader_adv = _started_parent_only(bot_active=False)
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_PARENT_ADV_ID},
        loader_complex_advs=[loader_adv],
    )
    decision = result.decision_for(_PARENT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)

    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED
    assert decision.reason_code == REASON_MANAGED_LOADER_OWNERSHIP
    assert not CampaignCollectionRouteResolver.is_management_relationship_proven(
        decision
    )
    assert CampaignCollectionRouteResolver.is_managed_collector_write_eligible(decision)


@pytest.mark.unit
def test_task_34_s05_refused_managed_no_unmanaged_duplicate() -> None:
    """3.4 / S05,S14,S19: ``refused`` в loader → MANAGED; без UNMANAGED duplicate."""
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_PARENT_ADV_ID, _SEARCH_ADV_ID},
        loader_complex_advs=[_refused_parent_with_search()],
    )
    full_routes = result.routes_by_grain(CampaignCollectionGrain.FULL_ADV_WB_STAT)

    for adv_id in (_PARENT_ADV_ID, _SEARCH_ADV_ID):
        assert full_routes[adv_id] is CollectionRoute.MANAGED
        decision = result.decision_for(adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT)
        assert decision is not None
        assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
            decision
        )
    assert CollectionRoute.UNMANAGED not in full_routes.values()


@pytest.mark.unit
def test_task_35_s06_s07_done_and_no_enrollment_unmanaged() -> None:
    """3.5 / S06,S07: ``done`` вне loader и нет enrollment → UNMANAGED при discovery."""
    resolver = CampaignCollectionRouteResolver()
    discovered = frozenset({_DONE_ADV_ID, _WB_ONLY_ADV_ID})

    done_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_DONE_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )
    wb_only_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )

    for decision in (done_decision, wb_only_decision):
        assert decision.route is CollectionRoute.UNMANAGED
        assert decision.reason_code == REASON_UNMANAGED_WB_DISCOVERY
        assert not CampaignCollectionRouteResolver.is_managed_collector_write_eligible(
            decision
        )


@pytest.mark.unit
def test_task_36_s08_search_leg_managed_full_adv_grain() -> None:
    """3.6 / S08: search leg через ``all_adv_ids`` → MANAGED ``full_adv_wb_stat``."""
    result = CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids={_SEARCH_ADV_ID},
        loader_complex_advs=[_refused_parent_with_search()],
    )
    decision = result.decision_for(_SEARCH_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)

    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED
    assert decision.reason_code == REASON_MANAGED_LOADER_OWNERSHIP
    assert CampaignCollectionRouteResolver.is_managed_collector_write_eligible(decision)
    assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        decision
    )


@pytest.mark.unit
def test_task_37_s09_managed_ownership_blocks_unmanaged_write_eligibility() -> None:
    """3.7 / S09: managed ownership → unmanaged MUST NOT write тот же grain в tick."""
    loader_adv = _refused_parent_with_search()
    tick_input = RouteResolverTickInput(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=frozenset({_PARENT_ADV_ID, _SEARCH_ADV_ID, _WB_ONLY_ADV_ID}),
        loader_complex_advs=(loader_adv,),
    )
    result = CampaignCollectionRouteResolver().resolve_tick(tick_input)
    full_routes = result.routes_by_grain(CampaignCollectionGrain.FULL_ADV_WB_STAT)

    for adv_id in (_PARENT_ADV_ID, _SEARCH_ADV_ID):
        assert full_routes[adv_id] is CollectionRoute.MANAGED
        decision = result.decision_for(adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT)
        assert decision is not None
        assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
            decision
        )

    wb_only = result.decision_for(_WB_ONLY_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)
    assert wb_only is not None
    assert wb_only.route is CollectionRoute.UNMANAGED
    assert CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(wb_only)


@pytest.mark.unit
def test_task_38_s15_unknown_fail_closed_no_write_no_enrollment() -> None:
    """3.8 / S15: неоднозначный id → UNKNOWN; fail-closed без write/enrollment."""
    resolver = CampaignCollectionRouteResolver()
    orphan_id = 404_404
    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=orphan_id,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=frozenset(),
        managed_ownership_adv_ids=frozenset(),
    )

    assert decision.route is CollectionRoute.UNKNOWN
    assert decision.reason_code == REASON_UNKNOWN_NOT_CLASSIFIED
    assert not CampaignCollectionRouteResolver.is_managed_collector_write_eligible(
        decision
    )
    assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        decision
    )
    assert not CampaignCollectionRouteResolver.is_management_relationship_proven(
        decision
    )


@pytest.mark.unit
def test_task_39_s21_bot_active_and_presence_not_ownership_proof() -> None:
    """3.9 / S21: ``bot_active`` и presence-only PG не proof ownership; нет provenance col."""
    resolver = CampaignCollectionRouteResolver()
    discovered = frozenset({_DONE_ADV_ID, _WB_ONLY_ADV_ID})

    # ``done`` + ``bot_active=True`` в PG, но post-filter loader отсекает строку.
    done_bot_active_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_DONE_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )
    assert done_bot_active_decision.route is CollectionRoute.UNMANAGED

    # Presence-only: PG row с пустыми nmids не попадает в loader → не MANAGED.
    wb_only_decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=discovered,
        managed_ownership_adv_ids=frozenset(),
    )
    assert wb_only_decision.route is CollectionRoute.UNMANAGED
    assert not CampaignCollectionRouteResolver.is_management_relationship_proven(
        wb_only_decision
    )

    provenance_fields = {
        name
        for name, attr in AdvSetting.__dict__.items()
        if isinstance(attr, Mapped) and "provenance" in name.lower()
    }
    assert provenance_fields == set()
