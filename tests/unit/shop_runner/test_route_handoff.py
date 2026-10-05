"""Handoff UNMANAGED ↔ MANAGED и reconcile — tasks 7.1–7.5 (S16–S19, S22).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

TARGET_REGRESSION для connect/disconnect/overlap/reconcile без wiring в
``WBShop.run``. Routing predicate и pre-write gate не stub'ятся.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats, FullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_wide_collection.full_adv_read_latest import (
    load_read_latest_full_adv_facts,
)
from app.modules.shop_runner.shop_wide_collection.route_handoff import (
    connect_handoff_newly_managed_adv_ids,
    done_handoff_transitioned_to_unmanaged,
    evaluate_refused_disconnect_like_handoff,
    resolve_connect_handoff_next_tick,
    resolve_done_disconnect_handoff,
    unmanaged_blocked_adv_ids_after_connect,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CollectionRoute,
    RouteResolverTickInput,
)
from app.modules.shop_runner.shop_wide_collection.route_transition_reconcile import (
    COLLECTOR_ROUTE_TRANSITION_RECONCILE,
    REASON_ROUTE_TRANSITION_RECONCILE,
    read_latest_grain_keys,
    reconcile_route_transition_read_latest,
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

_SHOP_ID = "shop-route-handoff"
_CONNECT_ADV_ID = 888_501
_DONE_ADV_ID = 888_502
_REFUSED_ADV_ID = 888_503
_STAT_DATE = "2026-10-04"
_T0 = datetime(2026, 10, 5, 3, 0, 0, tzinfo=timezone.utc)


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


class InMemoryHandoffStore:
    """Inventory + availability + full_adv read-latest для handoff tests."""

    def __init__(self) -> None:
        self.inventory_rows: list[dict[str, object]] = []
        self.availability_rows: list[dict[str, object]] = []
        self.full_adv_rows: list[dict[str, object]] = []

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        params = dict(parameters or {})
        stripped = query.strip()
        if stripped.startswith("SELECT") and "shop_campaign_inventory" in query:
            return _QueryRowsResult(self._select_inventory(query, params))
        if "full_adv_wb_stat" in query and "argMax" in query:
            return _QueryRowsResult(self._select_read_latest_full_adv(params))
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
        if "discovered_at" in query:
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
        return [
            (row["adv_id"], row["route"], row["route_version"])
            for row in latest.values()
        ]

    def _select_read_latest_full_adv(
        self, params: Mapping[str, object]
    ) -> list[tuple[object, ...]]:
        adv_ids = _as_int_set(params["adv_ids"])
        grouped: dict[tuple[int, str], dict[str, object]] = {}
        for row in self.full_adv_rows:
            adv_id = int(row["adv_id"])  # type: ignore[arg-type]
            if adv_id not in adv_ids:
                continue
            date_key = str(row["date"])
            key = (adv_id, date_key)
            current = grouped.get(key)
            row_version = float(row["version"])
            if current is None or row_version >= float(current["version"]):
                grouped[key] = dict(row)
        return [
            (
                adv_id,
                date_key,
                row["views"],
                row["clicks"],
                row["spend"],
                row["orders"],
                float(row["version"]),
            )
            for (adv_id, date_key), row in sorted(grouped.items())
        ]

    def seed_dual_leg_full_adv(
        self,
        adv_id: int,
        *,
        managed_views: int,
        unmanaged_views: int,
    ) -> None:
        """Dual-leg history: managed leg (lower version) + unmanaged leg (higher)."""
        self.full_adv_rows.extend(
            [
                {
                    "adv_id": adv_id,
                    "date": _STAT_DATE,
                    "views": managed_views,
                    "clicks": 1,
                    "spend": 5.0,
                    "orders": 1,
                    "version": "1.1",
                },
                {
                    "adv_id": adv_id,
                    "date": _STAT_DATE,
                    "views": unmanaged_views,
                    "clicks": 2,
                    "spend": 10.0,
                    "orders": 2,
                    "version": "1.2",
                },
            ]
        )

    def seed_inventory(
        self,
        *,
        adv_id: int,
        route: str,
        route_version: int,
    ) -> None:
        self.inventory_rows.append(
            {
                "shop_id": _SHOP_ID,
                "adv_id": adv_id,
                "nm_ids": [42],
                "wb_status": "9",
                "wb_lifecycle": "active",
                "route": route,
                "discovered_at": _T0.replace(tzinfo=None),
                "last_seen_at": _T0.replace(tzinfo=None),
                "route_version": route_version,
                "version": route_version,
            }
        )


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
    bot_active: bool = False,
    setting_id: int = 1,
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


def _complex_adv(*, adv_id: int, active_status: str, bot_active: bool = False) -> ComplexAdv:
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=_setting(
            adv_id=adv_id,
            nmids=[100],
            active_status=active_status,
            bot_active=bot_active,
            setting_id=adv_id,
        ),
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
        dates=[_STAT_DATE],
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

    async def insert(self, stats: Iterable[FullAdvStat]) -> None:
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


class _OverlapConnectGateReader:
    """Gate read после connect: epoch/route сменились во время in-flight tick."""

    def __init__(
        self,
        inner: InMemoryHandoffStore,
        *,
        adv_id: int,
        post_connect_route: str,
        post_connect_route_version: int,
    ) -> None:
        self._inner = inner
        self._adv_id = adv_id
        self._post_connect_route = post_connect_route
        self._post_connect_route_version = post_connect_route_version

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        if (
            query.strip().startswith("SELECT")
            and "argMax(route_version, version)" in query
        ):
            params = dict(parameters or {})
            adv_ids = _as_int_set(params["adv_ids"])
            if self._adv_id in adv_ids:
                return _QueryRowsResult(
                    [
                        (
                            self._adv_id,
                            self._post_connect_route,
                            self._post_connect_route_version,
                        )
                    ]
                )
        return await self._inner.query(query, parameters)


def _forbid(*_args: object, **_kwargs: object) -> Any:
    raise AssertionError("forbidden side effect")


@pytest.fixture
def forbid_management_and_forbidden_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
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


@pytest.mark.unit
def test_task_71_s16_connect_handoff_managed_unmanaged_blocked_management_unproven() -> None:
    """7.1 / S16: post-connect → MANAGED; unmanaged blocked; connect unproven."""
    discovered = frozenset({_CONNECT_ADV_ID})
    handoff = resolve_connect_handoff_next_tick(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=discovered,
        loader_before_connect=(),
        loader_after_connect=(_complex_adv(adv_id=_CONNECT_ADV_ID, active_status="started"),),
        connect_adv_ids=frozenset({_CONNECT_ADV_ID}),
    )
    newly_managed = connect_handoff_newly_managed_adv_ids(handoff)
    blocked = unmanaged_blocked_adv_ids_after_connect(handoff)

    assert _CONNECT_ADV_ID in newly_managed
    assert blocked == frozenset({_CONNECT_ADV_ID})
    after_decision = handoff.tick_after_connect.decision_for(
        _CONNECT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    assert after_decision is not None
    assert after_decision.route is CollectionRoute.MANAGED
    assert not CampaignCollectionRouteResolver.is_management_relationship_proven(
        after_decision
    )
    assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        after_decision
    )


@pytest.mark.asyncio
async def test_task_71_s16_post_connect_unmanaged_collect_no_fact_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.1 / S16: после connect unmanaged orchestrator MUST NOT писать owned grain."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    writer = _RecordingFullAdvWriter()
    fetcher = _RecordingFetcher({_CONNECT_ADV_ID: [_sample_full_adv_stat(_CONNECT_ADV_ID)]})
    loader_after = (_complex_adv(adv_id=_CONNECT_ADV_ID, active_status="started"),)

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=loader_after,
        campaigns_discovery=_StubDiscovery([_Advert(_CONNECT_ADV_ID)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert _CONNECT_ADV_ID not in result.unmanaged_eligible_adv_ids
    assert writer.insert_calls == []
    assert fetcher.calls == []


@pytest.mark.asyncio
async def test_task_72_s17_overlap_connect_stale_epoch_blocks_write_no_double_count(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.2 / S17: overlap connect — stale epoch/ownership blocks fact write; argMax dedup."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    store.seed_dual_leg_full_adv(
        _CONNECT_ADV_ID,
        managed_views=50,
        unmanaged_views=99,
    )
    writer = _RecordingFullAdvWriter()
    fetcher = _RecordingFetcher({_CONNECT_ADV_ID: [_sample_full_adv_stat(_CONNECT_ADV_ID)]})
    overlap_reader = _OverlapConnectGateReader(
        store,
        adv_id=_CONNECT_ADV_ID,
        post_connect_route=CollectionRoute.MANAGED.value,
        post_connect_route_version=2,
    )

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_CONNECT_ADV_ID)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        route_reader=overlap_reader,
        observed_at=_T0,
    )

    outcome = next(o for o in result.outcomes if o.adv_id == _CONNECT_ADV_ID)
    assert outcome.fact_write_succeeded is False
    assert outcome.availability_reason_code in {
        REASON_ROUTE_EPOCH_STALE,
        REASON_OWNERSHIP_MISMATCH,
    }
    assert writer.insert_calls == []
    avail = store.availability_rows[-1]
    assert avail["route_version"] == 2
    assert avail["reason_code"] == outcome.availability_reason_code
    assert avail["collector_id"] == COLLECTOR_UNMANAGED_FULL_ADV

    read_latest = await load_read_latest_full_adv_facts(
        store, adv_ids=(_CONNECT_ADV_ID,)
    )
    assert len(read_latest) == 1
    assert read_latest[0].views == 99
    assert len(read_latest_grain_keys(read_latest)) == 1


@pytest.mark.asyncio
async def test_task_72_s17_overlap_current_epoch_allows_inflight_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.2 / S17: in-flight MAY complete when epoch current and ownership matches."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    writer = _RecordingFullAdvWriter()
    stat = _sample_full_adv_stat(_CONNECT_ADV_ID)
    fetcher = _RecordingFetcher({_CONNECT_ADV_ID: [stat]})

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_CONNECT_ADV_ID)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    outcome = next(o for o in result.outcomes if o.adv_id == _CONNECT_ADV_ID)
    assert outcome.fact_write_succeeded is True
    assert outcome.availability_reason_code == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED
    assert len(writer.insert_calls) == 1
    avail = store.availability_rows[-1]
    assert avail["route_version"] == outcome.checked_route_version


def test_task_72_s17_gate_pure_overlap_ownership_mismatch() -> None:
    """7.2 / S17: gate unit — connect overlap ownership mismatch blocks write."""
    resolver = CampaignCollectionRouteResolver()
    decision = resolver.resolve_route(
        shop_id=_SHOP_ID,
        wb_adv_id=_CONNECT_ADV_ID,
        grain=CampaignCollectionGrain.FULL_ADV_WB_STAT,
        wb_discovered_adv_ids=frozenset({_CONNECT_ADV_ID}),
        managed_ownership_adv_ids=frozenset(),
    )
    gate = evaluate_unmanaged_fact_write_gate(
        RouteWriteGateInput(
            shop_id=_SHOP_ID,
            adv_id=_CONNECT_ADV_ID,
            observed_route_version=1,
            current_inventory=InventoryRouteSnapshot(
                adv_id=_CONNECT_ADV_ID,
                route=CollectionRoute.MANAGED.value,
                route_version=2,
            ),
            route_decision=decision,
        )
    )
    assert gate.allow_fact_write is False
    assert gate.reason_code == REASON_OWNERSHIP_MISMATCH
    assert gate.checked_route_version == 2


@pytest.mark.unit
def test_task_73_s18_done_disconnect_transitions_to_unmanaged() -> None:
    """7.3 / S18: terminal done → stop managed; resume UNMANAGED при WB discovery."""
    discovered = frozenset({_DONE_ADV_ID})
    loader_before = (_complex_adv(adv_id=_DONE_ADV_ID, active_status="started"),)
    handoff = resolve_done_disconnect_handoff(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=discovered,
        loader_before_done=loader_before,
        loader_after_done=(),
        done_adv_ids=frozenset({_DONE_ADV_ID}),
    )
    transitioned = done_handoff_transitioned_to_unmanaged(handoff)

    assert transitioned == frozenset({_DONE_ADV_ID})
    after_decision = handoff.tick_after_done.decision_for(
        _DONE_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    assert after_decision is not None
    assert after_decision.route is CollectionRoute.UNMANAGED
    assert CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        after_decision
    )
    before_decision = handoff.tick_before_done.decision_for(
        _DONE_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    assert before_decision is not None
    assert before_decision.route is CollectionRoute.MANAGED


@pytest.mark.asyncio
async def test_task_73_s18_done_handoff_ch_history_retained(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.3 / S18: CH history по adv_id retained после done handoff."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    store.seed_dual_leg_full_adv(_DONE_ADV_ID, managed_views=77, unmanaged_views=88)
    read_latest = await load_read_latest_full_adv_facts(
        store, adv_ids=(_DONE_ADV_ID,)
    )
    assert len(read_latest) == 1
    assert read_latest[0].adv_id == _DONE_ADV_ID
    assert read_latest[0].views == 88


@pytest.mark.asyncio
async def test_task_73_s18_done_unmanaged_collect_resumes(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.3 / S18: после done unmanaged collector MAY писать fact grain."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    writer = _RecordingFullAdvWriter()
    fetcher = _RecordingFetcher({_DONE_ADV_ID: [_sample_full_adv_stat(_DONE_ADV_ID)]})

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_DONE_ADV_ID)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert _DONE_ADV_ID in result.unmanaged_eligible_adv_ids
    assert len(writer.insert_calls) == 1


@pytest.mark.unit
def test_task_74_s19_refused_stays_managed_on_disconnect_like_event() -> None:
    """7.4 / S19: refused MUST NOT переводить ownership на unmanaged alone."""
    result = evaluate_refused_disconnect_like_handoff(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=frozenset({_REFUSED_ADV_ID}),
        loader_with_refused=(
            _complex_adv(adv_id=_REFUSED_ADV_ID, active_status="refused", bot_active=False),
        ),
    )

    assert result.all_remain_managed is True
    assert _REFUSED_ADV_ID in result.refused_adv_ids
    decision = result.tick_result.decision_for(
        _REFUSED_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    assert decision is not None
    assert decision.route is CollectionRoute.MANAGED
    assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
        decision
    )


@pytest.mark.asyncio
async def test_task_74_s19_refused_unmanaged_collect_blocked(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.4 / S19: refused managed loader → unmanaged MUST NOT duplicate grain."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    writer = _RecordingFullAdvWriter()
    fetcher = _RecordingFetcher({_REFUSED_ADV_ID: [_sample_full_adv_stat(_REFUSED_ADV_ID)]})
    loader = (_complex_adv(adv_id=_REFUSED_ADV_ID, active_status="refused"),)

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=loader,
        campaigns_discovery=_StubDiscovery([_Advert(_REFUSED_ADV_ID)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert _REFUSED_ADV_ID not in result.unmanaged_eligible_adv_ids
    assert writer.insert_calls == []


@pytest.mark.asyncio
async def test_task_75_s22_reconcile_dual_leg_records_availability_no_fact_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.5 / S22: reconcile dual-leg → route_transition_reconcile; no fact write."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    store.seed_dual_leg_full_adv(
        _CONNECT_ADV_ID,
        managed_views=30,
        unmanaged_views=40,
    )
    store.seed_inventory(
        adv_id=_CONNECT_ADV_ID,
        route=CollectionRoute.MANAGED.value,
        route_version=3,
    )
    resolver = CampaignCollectionRouteResolver()
    tick = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=_SHOP_ID,
            wb_discovered_adv_ids=frozenset({_CONNECT_ADV_ID}),
            loader_complex_advs=(
                _complex_adv(adv_id=_CONNECT_ADV_ID, active_status="started"),
            ),
        )
    )
    decision = tick.decision_for(
        _CONNECT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    raw_rows = list(store.full_adv_rows)

    outcomes = await reconcile_route_transition_read_latest(
        shop_id=_SHOP_ID,
        adv_ids=(_CONNECT_ADV_ID,),
        route_decisions={_CONNECT_ADV_ID: decision},
        observed_route_versions={_CONNECT_ADV_ID: 3},
        inventory_reader=store,
        full_adv_reader=store,
        availability_client=store,
        raw_dual_leg_rows=raw_rows,
    )

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.dual_leg_detected is True
    assert outcome.availability_reason_code == REASON_ROUTE_TRANSITION_RECONCILE
    assert outcome.checked_route_version == 3
    assert outcome.allow_fact_write is False
    assert outcome.read_latest_grain_count == 1
    assert len(outcome.read_latest_rows) == 1
    assert outcome.read_latest_rows[0].views == 40

    avail = store.availability_rows[-1]
    assert avail["reason_code"] == REASON_ROUTE_TRANSITION_RECONCILE
    assert avail["route_version"] == 3
    assert avail["collector_id"] == COLLECTOR_ROUTE_TRANSITION_RECONCILE


@pytest.mark.asyncio
async def test_task_75_s22_reconcile_stale_epoch_no_fact_write(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.5 / S22: stale route_version at reconcile → MUST NOT write fact grain."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    store.seed_dual_leg_full_adv(_CONNECT_ADV_ID, managed_views=10, unmanaged_views=20)
    store.seed_inventory(
        adv_id=_CONNECT_ADV_ID,
        route=CollectionRoute.MANAGED.value,
        route_version=5,
    )
    resolver = CampaignCollectionRouteResolver()
    tick = resolver.resolve_tick(
        RouteResolverTickInput(
            shop_id=_SHOP_ID,
            wb_discovered_adv_ids=frozenset({_CONNECT_ADV_ID}),
            loader_complex_advs=(
                _complex_adv(adv_id=_CONNECT_ADV_ID, active_status="started"),
            ),
        )
    )
    decision = tick.decision_for(
        _CONNECT_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )

    outcomes = await reconcile_route_transition_read_latest(
        shop_id=_SHOP_ID,
        adv_ids=(_CONNECT_ADV_ID,),
        route_decisions={_CONNECT_ADV_ID: decision},
        observed_route_versions={_CONNECT_ADV_ID: 3},
        inventory_reader=store,
        full_adv_reader=store,
        availability_client=store,
        raw_dual_leg_rows=list(store.full_adv_rows),
    )

    outcome = outcomes[0]
    assert outcome.allow_fact_write is False
    assert outcome.checked_route_version == 5
    assert outcome.availability_reason_code == REASON_ROUTE_TRANSITION_RECONCILE
    avail = store.availability_rows[-1]
    assert avail["route_version"] == 5


@pytest.mark.asyncio
async def test_task_75_s22_read_latest_no_double_count_dual_leg(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """7.5 / S22: read-latest MUST NOT double-count declared grains."""
    del forbid_management_and_forbidden_seams
    store = InMemoryHandoffStore()
    store.seed_dual_leg_full_adv(_CONNECT_ADV_ID, managed_views=1, unmanaged_views=2)
    read_latest = await load_read_latest_full_adv_facts(
        store, adv_ids=(_CONNECT_ADV_ID,)
    )
    assert len(read_latest) == 1
    assert len(read_latest_grain_keys(read_latest)) == 1
    assert read_latest[0].views == 2
