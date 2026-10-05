"""Unmanaged campaign advertising collector — tasks 4.1–4.4 (S10, S13, route gate).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Проверяет ``collect_unmanaged_campaign_advertising`` на injectable seams.
Production wiring — ``tick_wiring`` / ``CoroutinesManager`` (§8.1).
Gate ``route_version``/ownership не подменяется stub'om routing predicate.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import ast
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats, FullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CollectionRoute,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_UNMANAGED_FULL_ADV,
    REASON_OWNERSHIP_MISMATCH,
    REASON_ROUTE_EPOCH_STALE,
    REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
    InventoryRouteSnapshot,
    RouteWriteGateInput,
    evaluate_unmanaged_fact_write_gate,
)
from app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator import (
    collect_unmanaged_campaign_advertising,
)

_SHOP_ID = "shop-unmanaged-collector"
_WB_ONLY_ADV_ID = 888_001
_MANAGED_ADV_ID = 101
_T0 = datetime(2026, 10, 5, 1, 0, 0, tzinfo=timezone.utc)


class _Nm:
    def __init__(self, nm_id: int) -> None:
        self.nm_id = nm_id


class _Advert:
    def __init__(self, adv_id: int, status: int = 9, nm_ids: tuple[int, ...] = (42,)) -> None:
        self.id = adv_id
        self.status = status
        self.nm_settings: tuple[_Nm, ...] = tuple(_Nm(nm_id) for nm_id in nm_ids)


class _QueryRowsResult:
    def __init__(self, result_rows: Sequence[Sequence[object]]) -> None:
        self.result_rows = result_rows


class InMemoryShopWideClickHouse:
    """Inventory + availability + route snapshot read на одном injected клиенте."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.inventory_rows: list[dict[str, object]] = []
        self.availability_rows: list[dict[str, object]] = []

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        params = dict(parameters or {})
        self.queries.append((query, params))
        stripped = query.strip()
        if stripped.startswith("SELECT") and "shop_campaign_inventory" in query:
            return _QueryRowsResult(self._select_inventory(query, params))
        if stripped.startswith("INSERT INTO default_db.shop_campaign_inventory"):
            self.inventory_rows.append(dict(params))
            return _QueryRowsResult(())
        if stripped.startswith("INSERT INTO default_db.shop_campaign_collection_availability"):
            self.availability_rows.append(dict(params))
            return _QueryRowsResult(())
        raise AssertionError(f"unexpected query: {query}")

    def _select_inventory(
        self, query: str, params: Mapping[str, object]
    ) -> list[tuple[object, ...]]:
        if "argMax(route_version, version)" in query and "discovered_at" not in query:
            return self._select_route_snapshot(params)
        if "discovered_at" in query:
            return self._select_inventory_full(params)
        raise AssertionError(f"unexpected inventory select: {query}")

    def _select_inventory_full(
        self, params: Mapping[str, object]
    ) -> list[tuple[object, ...]]:
        shop_id = params["shop_id"]
        adv_ids = _as_int_set(params["adv_ids"])
        latest: dict[int, dict[str, object]] = {}
        for row in self.inventory_rows:
            adv_id = row["adv_id"]
            if row["shop_id"] != shop_id or adv_id not in adv_ids:
                continue
            current = latest.get(int(adv_id))  # type: ignore[arg-type]
            if current is None or _version(row) >= _version(current):
                latest[int(adv_id)] = row  # type: ignore[arg-type]
        return [
            (
                row["adv_id"],
                row["route"],
                row["route_version"],
                row["version"],
                row["discovered_at"],
            )
            for row in latest.values()
        ]

    def _select_route_snapshot(
        self, params: Mapping[str, object]
    ) -> list[tuple[object, ...]]:
        shop_id = params["shop_id"]
        adv_ids = _as_int_set(params["adv_ids"])
        latest: dict[int, dict[str, object]] = {}
        for row in self.inventory_rows:
            adv_id = row["adv_id"]
            if row["shop_id"] != shop_id or adv_id not in adv_ids:
                continue
            current = latest.get(int(adv_id))  # type: ignore[arg-type]
            if current is None or _version(row) >= _version(current):
                latest[int(adv_id)] = row  # type: ignore[arg-type]
        return [
            (row["adv_id"], row["route"], row["route_version"])
            for row in latest.values()
        ]

    def bump_route_epoch(
        self,
        *,
        shop_id: str,
        adv_id: int,
        new_route: str,
    ) -> None:
        """Симулирует handoff: новая inventory строка с увеличенным route_version."""
        current = self._latest_inventory_row(shop_id, adv_id)
        if current is None:
            raise AssertionError("no inventory row to bump")
        self.inventory_rows.append(
            {
                "shop_id": shop_id,
                "adv_id": adv_id,
                "nm_ids": list(current["nm_ids"]),
                "wb_status": current["wb_status"],
                "wb_lifecycle": current["wb_lifecycle"],
                "route": new_route,
                "discovered_at": current["discovered_at"],
                "last_seen_at": current["last_seen_at"],
                "route_version": int(current["route_version"]) + 1,
                "version": int(current["version"]) + 1,
            }
        )

    def _latest_inventory_row(
        self, shop_id: str, adv_id: int
    ) -> dict[str, object] | None:
        latest: dict[str, object] | None = None
        for row in self.inventory_rows:
            if row["shop_id"] == shop_id and row["adv_id"] == adv_id:
                if latest is None or _version(row) >= _version(latest):
                    latest = row
        return latest


def _version(row: Mapping[str, object]) -> int:
    value = row["version"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError("version must be int")
    return value


def _as_int_set(raw: object) -> set[int]:
    if not isinstance(raw, list):
        raise AssertionError("adv_ids must be list")
    result: set[int] = set()
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise AssertionError("adv_id must be int")
        result.add(item)
    return result


def _setting(
    *,
    adv_id: int,
    nmids: list[int],
    active_status: str,
    bot_active: bool,
    setting_id: int,
) -> MagicMock:
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


def _managed_loader_adv(*, bot_active: bool = False) -> ComplexAdv:
    parent = _setting(
        adv_id=_MANAGED_ADV_ID,
        nmids=[555],
        active_status="started",
        bot_active=bot_active,
        setting_id=1,
    )
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=parent,
        search_adv=None,
        target_pay_for_order=None,
    )


def _sample_full_adv_stat(adv_id: int) -> FullAdvStat:
    day = DayStats(
        date=datetime(2026, 10, 4),
        views=10,
        clicks=2,
        ctr=20.0,
        cpc=5.0,
        sum=10.0,
        atbs=1,
        orders=1,
        cr=50.0,
        shks=1,
        sum_price=100.0,
    )
    return FullAdvStat(
        dates=["2026-10-04"],
        views=10,
        clicks=2,
        ctr=20.0,
        cpc=5.0,
        sum=10.0,
        atbs=1,
        orders=1,
        cr=50.0,
        shks=1,
        sum_price=100.0,
        days=[day],
        boosterStats=None,
        advertId=adv_id,
    )


class _StubDiscovery:
    def __init__(self, items: Sequence[_Advert]) -> None:
        self._items = items

    async def get_all_campaigns(self) -> Sequence[_Advert]:
        return self._items


class _RecordingFullAdvWriter:
    def __init__(self) -> None:
        self.insert_calls: list[list[FullAdvStat]] = []

    async def insert(self, stats: Sequence[FullAdvStat]) -> None:
        self.insert_calls.append(list(stats))


class _RecordingFetcher:
    def __init__(self, stats_by_id: Mapping[int, list[FullAdvStat]]) -> None:
        self._stats_by_id = stats_by_id
        self.calls: list[set[int]] = []

    async def get_full_adv_stat_for_adv_ids(
        self,
        adv_ids: set[int],
        threshold_dates: int,
    ) -> list[FullAdvStat]:
        self.calls.append(set(adv_ids))
        _ = threshold_dates
        result: list[FullAdvStat] = []
        for adv_id in adv_ids:
            result.extend(self._stats_by_id.get(adv_id, []))
        return result


class _GateStaleRouteReader:
    """Gate read возвращает устаревший epoch; upsert SELECT идёт во inner."""

    def __init__(
        self,
        inner: InMemoryShopWideClickHouse,
        stale: InventoryRouteSnapshot,
    ) -> None:
        self._inner = inner
        self._stale = stale

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        if (
            query.strip().startswith("SELECT")
            and "argMax(route_version, version)" in query
            and "discovered_at" not in query
        ):
            params = dict(parameters or {})
            adv_ids = _as_int_set(params["adv_ids"])
            if self._stale.adv_id in adv_ids:
                return _QueryRowsResult(
                    [
                        (
                            self._stale.adv_id,
                            self._stale.route,
                            self._stale.route_version,
                        )
                    ]
                )
        return await self._inner.query(query, parameters)


def _forbid(*_args: object, **_kwargs: object) -> Any:
    raise AssertionError("forbidden side effect")


@pytest.fixture
def forbid_management_and_forbidden_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    """S10/S13: collection MUST NOT enrollment, funnel, clusters, management."""
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.insert",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.common_sale_stat_updater."
        "clickhouse_common_stat_manager.ClickHouseCommonStatManager.insert",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.ClustersAdvStatUpdater",
        _forbid,
    )
    monkeypatch.setattr(
        "app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter."
        "CampaignsInfoV2Adapter.get_all_campaigns",
        _forbid,
    )


def test_orchestrator_module_forbids_forbidden_imports() -> None:
    """Статический контракт: orchestrator не импортирует forbidden seams."""
    import app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            for alias in node.names:
                imported_names.add(alias.name)
    forbidden_modules = {
        "app.modules.shop_runner.service_manager.services.common_sale_stat_updater",
        "app.modules.shop_runner.clusters_adv_stat_updater",
        "app.modules.common_slaves.wildberries.wb_db_manager",
        "app.modules.shop_runner.service_manager.manager",
        "app.modules.full_stat_adv_updater.wb_data_getter",
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat",
    }
    forbidden_names = {
        "ClustersAdvStatUpdater",
        "ClickHouseCommonStatManager",
        "get_sales_funnel_products_history",
        "update_advs_in_db",
        "AdvSetting",
    }
    for name in forbidden_modules:
        assert name not in imported
    for token in forbidden_names:
        assert token not in imported_names


@pytest.mark.asyncio
async def test_task_42_s10_unmanaged_collect_no_enrollment_side_effects(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """S10: успешный unmanaged collect → no AdvSetting create, bot_active unchanged."""
    del forbid_management_and_forbidden_seams
    client = InMemoryShopWideClickHouse()
    writer = _RecordingFullAdvWriter()
    stat = _sample_full_adv_stat(_WB_ONLY_ADV_ID)
    fetcher = _RecordingFetcher({_WB_ONLY_ADV_ID: [stat]})
    loader_adv = _managed_loader_adv(bot_active=False)
    initial_bot_active = loader_adv.adv_setting.bot_active

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(loader_adv,),
        campaigns_discovery=_StubDiscovery(
            [_Advert(_WB_ONLY_ADV_ID), _Advert(_MANAGED_ADV_ID)]
        ),
        inventory_client=client,
        availability_client=client,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert _WB_ONLY_ADV_ID in result.unmanaged_eligible_adv_ids
    assert _MANAGED_ADV_ID not in result.unmanaged_eligible_adv_ids
    assert len(writer.insert_calls) == 1
    assert writer.insert_calls[0][0].advertId == _WB_ONLY_ADV_ID
    assert loader_adv.adv_setting.bot_active is initial_bot_active
    assert result.full_adv_stats_written == 1
    outcome = next(o for o in result.outcomes if o.adv_id == _WB_ONLY_ADV_ID)
    assert outcome.fact_write_succeeded is True
    assert outcome.availability_reason_code == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED


@pytest.mark.asyncio
async def test_task_43_s13_unmanaged_writes_full_adv_only_not_forbidden_seams(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """S13: unmanaged пишет full_adv_wb_stat only; forbidden CH grains отсутствуют."""
    del forbid_management_and_forbidden_seams
    client = InMemoryShopWideClickHouse()
    writer = _RecordingFullAdvWriter()
    stat = _sample_full_adv_stat(_WB_ONLY_ADV_ID)
    fetcher = _RecordingFetcher({_WB_ONLY_ADV_ID: [stat]})

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_WB_ONLY_ADV_ID)]),
        inventory_client=client,
        availability_client=client,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=3,
        observed_at=_T0,
    )

    assert len(writer.insert_calls) == 1
    assert writer.insert_calls[0][0].advertId == _WB_ONLY_ADV_ID
    assert result.full_adv_stats_written == 1
    assert fetcher.calls == [{_WB_ONLY_ADV_ID}]
    for query, _params in client.queries:
        assert "wb_common_stat" not in query
        assert "clusters_adv_stats" not in query
        assert "full_adv_wb_stat" not in query
    availability_collectors = {
        row["collector_id"] for row in client.availability_rows
    }
    assert availability_collectors == {COLLECTOR_UNMANAGED_FULL_ADV}


@pytest.mark.asyncio
async def test_task_44_route_epoch_stale_skips_fact_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """4.4: устаревший route_version на gate read → MUST NOT писать fact grain."""
    del forbid_management_and_forbidden_seams
    client = InMemoryShopWideClickHouse()
    writer = _RecordingFullAdvWriter()
    stat = _sample_full_adv_stat(_WB_ONLY_ADV_ID)
    fetcher = _RecordingFetcher({_WB_ONLY_ADV_ID: [stat]})
    stale_reader = _GateStaleRouteReader(
        client,
        InventoryRouteSnapshot(
            adv_id=_WB_ONLY_ADV_ID,
            route=CollectionRoute.MANAGED.value,
            route_version=99,
        ),
    )

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_WB_ONLY_ADV_ID)]),
        inventory_client=client,
        availability_client=client,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        route_reader=stale_reader,
        observed_at=_T0,
    )

    stale_outcome = next(o for o in result.outcomes if o.adv_id == _WB_ONLY_ADV_ID)
    assert stale_outcome.fact_write_succeeded is False
    assert stale_outcome.availability_reason_code in {
        REASON_ROUTE_EPOCH_STALE,
        REASON_OWNERSHIP_MISMATCH,
    }
    assert writer.insert_calls == []
    avail = client.availability_rows[-1]
    assert avail["route_version"] == 99
    assert avail["reason_code"] == stale_outcome.availability_reason_code


@pytest.mark.asyncio
async def test_task_44_route_epoch_current_allows_fact_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """4.4: актуальный route_version + UNMANAGED ownership → fact write разрешён."""
    del forbid_management_and_forbidden_seams
    client = InMemoryShopWideClickHouse()
    writer = _RecordingFullAdvWriter()
    stat = _sample_full_adv_stat(_WB_ONLY_ADV_ID)
    fetcher = _RecordingFetcher({_WB_ONLY_ADV_ID: [stat]})

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_WB_ONLY_ADV_ID)]),
        inventory_client=client,
        availability_client=client,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    outcome = next(o for o in result.outcomes if o.adv_id == _WB_ONLY_ADV_ID)
    assert outcome.fact_write_succeeded is True
    assert outcome.checked_route_version >= 1
    assert len(writer.insert_calls) == 1
    avail = client.availability_rows[-1]
    assert avail["route_version"] == outcome.checked_route_version
    assert avail["reason_code"] == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED


def test_route_write_gate_pure_stale_epoch() -> None:
    """Gate unit: epoch mismatch → allow_fact_write=False (gate не stub'ится)."""
    from app.modules.shop_runner.shop_wide_collection.route_resolver import (
        CampaignCollectionRouteResolver,
        CampaignRouteDecision,
        CampaignRouteKey,
    )

    resolver = CampaignCollectionRouteResolver()
    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=frozenset({_WB_ONLY_ADV_ID}),
        managed_ownership_adv_ids=frozenset(),
    )
    assert decision.route is CollectionRoute.UNMANAGED

    gate = evaluate_unmanaged_fact_write_gate(
        RouteWriteGateInput(
            shop_id=_SHOP_ID,
            adv_id=_WB_ONLY_ADV_ID,
            observed_route_version=1,
            current_inventory=InventoryRouteSnapshot(
                adv_id=_WB_ONLY_ADV_ID,
                route=CollectionRoute.UNMANAGED.value,
                route_version=2,
            ),
            route_decision=decision,
        )
    )
    assert gate.allow_fact_write is False
    assert gate.reason_code == REASON_ROUTE_EPOCH_STALE
    assert gate.checked_route_version == 2


def test_route_write_gate_pure_ownership_mismatch() -> None:
    """Gate unit: route managed при UNMANAGED collector → skip write."""
    from app.modules.shop_runner.shop_wide_collection.route_resolver import (
        CampaignCollectionRouteResolver,
    )

    resolver = CampaignCollectionRouteResolver()
    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_WB_ONLY_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=frozenset({_WB_ONLY_ADV_ID}),
        managed_ownership_adv_ids=frozenset(),
    )
    gate = evaluate_unmanaged_fact_write_gate(
        RouteWriteGateInput(
            shop_id=_SHOP_ID,
            adv_id=_WB_ONLY_ADV_ID,
            observed_route_version=2,
            current_inventory=InventoryRouteSnapshot(
                adv_id=_WB_ONLY_ADV_ID,
                route=CollectionRoute.MANAGED.value,
                route_version=2,
            ),
            route_decision=decision,
        )
    )
    assert gate.allow_fact_write is False
    assert gate.reason_code == REASON_OWNERSHIP_MISMATCH


@pytest.mark.asyncio
async def test_managed_only_discovery_fail_closed_no_unmanaged_fetch(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """Managed loader universe без WB-only ids → unmanaged fetch/write не стартует."""
    del forbid_management_and_forbidden_seams
    client = InMemoryShopWideClickHouse()
    writer = _RecordingFullAdvWriter()
    fetcher = _RecordingFetcher({})

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(_managed_loader_adv(),),
        campaigns_discovery=_StubDiscovery([_Advert(_MANAGED_ADV_ID)]),
        inventory_client=client,
        availability_client=client,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert result.unmanaged_eligible_adv_ids == frozenset()
    assert writer.insert_calls == []
    assert fetcher.calls == []
