"""Partial failure, availability append-only и read-latest (tasks 6.1–6.3).

Spec: ``connected-shop-campaign-ad-data-collection`` (S11, S12).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Integration-style unit: несколько кампаний, partial source failure,
append-only availability с ``route_version``, read-latest fact после ошибки.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats, FullAdvStat
from app.modules.shop_runner.shop_wide_collection.full_adv_read_latest import (
    load_read_latest_full_adv_facts,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CollectionRoute,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_UNMANAGED_FULL_ADV,
    REASON_COLLECTOR_SOURCE_ERROR,
    REASON_FACT_WRITE_ERROR,
    REASON_OWNERSHIP_MISMATCH,
    REASON_ROUTE_EPOCH_STALE,
    REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
    InventoryRouteSnapshot,
)
from app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator import (
    collect_unmanaged_campaign_advertising,
)

_SHOP_ID = "shop-partial-failure"
_ADV_OK_A = 888_101
_ADV_OK_B = 888_102
_ADV_FAIL = 888_103
_T0 = datetime(2026, 10, 5, 2, 0, 0, tzinfo=timezone.utc)
_STAT_DATE = "2026-10-04"


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


class InMemoryShopWideCollectStore:
    """Inventory + availability + full_adv facts для integration-style unit."""

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

    def record_full_adv_insert(
        self,
        stats: Iterable[FullAdvStat],
        *,
        version: str,
    ) -> None:
        for stat in stats:
            for day in stat.days:
                self.full_adv_rows.append(
                    {
                        "adv_id": stat.advertId,
                        "date": day.date.strftime("%Y-%m-%d"),
                        "views": day.views,
                        "clicks": day.clicks,
                        "spend": day.sum,
                        "orders": day.orders,
                        "version": version,
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


def _sample_full_adv_stat(adv_id: int, *, views: int = 10) -> FullAdvStat:
    day = DayStats(
        date=datetime(2026, 10, 4),
        views=views,
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
        views=views,
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


class _ChFullAdvWriter:
    """Пишет fact rows в in-memory store с monotonic version."""

    def __init__(self, store: InMemoryShopWideCollectStore) -> None:
        self._store = store
        self._version_counter = 0
        self.insert_calls: list[list[FullAdvStat]] = []

    async def insert(self, stats: Iterable[FullAdvStat]) -> None:
        batch = list(stats)
        self.insert_calls.append(batch)
        self._version_counter += 1
        self._store.record_full_adv_insert(
            batch,
            version=f"1.{self._version_counter}",
        )


class _PartialFailureFetcher:
    """Per-adv fetch: ``fail_adv_ids`` бросают source error."""

    def __init__(
        self,
        stats_by_id: Mapping[int, list[FullAdvStat]],
        *,
        fail_adv_ids: frozenset[int] = frozenset(),
    ) -> None:
        self._stats_by_id = stats_by_id
        self._fail_adv_ids = fail_adv_ids
        self.calls: list[set[int]] = []

    async def get_full_adv_stat_for_adv_ids(
        self,
        adv_ids: set[int],
        threshold_dates: int,
    ) -> list[FullAdvStat]:
        self.calls.append(set(adv_ids))
        _ = threshold_dates
        if len(adv_ids) != 1:
            raise AssertionError("partial failure tests expect per-adv fetch")
        adv_id = next(iter(adv_ids))
        if adv_id in self._fail_adv_ids:
            raise RuntimeError(f"wb source error adv_id={adv_id}")
        return list(self._stats_by_id.get(adv_id, []))


class _GateStaleRouteReader:
    """Gate read возвращает устаревший epoch; upsert SELECT идёт во inner."""

    def __init__(
        self,
        inner: InMemoryShopWideCollectStore,
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


class _FailInsertForAdvWriter:
    """Insert OK для всех adv_id кроме ``fail_adv_ids``."""

    def __init__(
        self,
        inner: _ChFullAdvWriter,
        *,
        fail_adv_ids: frozenset[int],
    ) -> None:
        self._inner = inner
        self._fail_adv_ids = fail_adv_ids

    async def insert(self, stats: Iterable[FullAdvStat]) -> None:
        batch = list(stats)
        if batch and batch[0].advertId in self._fail_adv_ids:
            raise RuntimeError(f"clickhouse insert failed adv_id={batch[0].advertId}")
        await self._inner.insert(batch)


def _forbid(*_args: object, **_kwargs: object) -> Any:
    raise AssertionError("forbidden side effect")


@pytest.fixture
def forbid_management_and_forbidden_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat.insert",
        _forbid,
    )


def _availability_for_adv(
    store: InMemoryShopWideCollectStore, adv_id: int
) -> list[dict[str, object]]:
    return [
        row
        for row in store.availability_rows
        if row["shop_id"] == _SHOP_ID and row["adv_id"] == adv_id
    ]


@pytest.mark.asyncio
async def test_task_61_s11_single_collector_failure_records_reason_and_continues(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """S11/6.1: source error одной кампании → reason_code; остальные продолжают."""
    del forbid_management_and_forbidden_seams
    store = InMemoryShopWideCollectStore()
    writer = _ChFullAdvWriter(store)
    fetcher = _PartialFailureFetcher(
        {
            _ADV_OK_A: [_sample_full_adv_stat(_ADV_OK_A)],
            _ADV_OK_B: [_sample_full_adv_stat(_ADV_OK_B, views=20)],
        },
        fail_adv_ids=frozenset({_ADV_FAIL}),
    )

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery(
            [
                _Advert(_ADV_OK_A),
                _Advert(_ADV_OK_B),
                _Advert(_ADV_FAIL),
            ]
        ),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert result.unmanaged_eligible_adv_ids == frozenset(
        {_ADV_OK_A, _ADV_OK_B, _ADV_FAIL}
    )
    assert len(writer.insert_calls) == 2
    failed_outcome = next(o for o in result.outcomes if o.adv_id == _ADV_FAIL)
    assert failed_outcome.fact_write_succeeded is False
    assert failed_outcome.availability_reason_code == REASON_COLLECTOR_SOURCE_ERROR
    for adv_id in (_ADV_OK_A, _ADV_OK_B):
        ok_outcome = next(o for o in result.outcomes if o.adv_id == adv_id)
        assert ok_outcome.fact_write_succeeded is True
        assert (
            ok_outcome.availability_reason_code
            == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED
        )
    fail_rows = _availability_for_adv(store, _ADV_FAIL)
    assert len(fail_rows) == 1
    assert fail_rows[0]["reason_code"] == REASON_COLLECTOR_SOURCE_ERROR
    assert fail_rows[0]["route_version"] >= 1


@pytest.mark.asyncio
async def test_task_62_s12_read_latest_retains_prior_success_after_failed_attempt(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """S12/6.2: prior CH success survives failed latest attempt (argMax read)."""
    del forbid_management_and_forbidden_seams
    store = InMemoryShopWideCollectStore()
    writer = _ChFullAdvWriter(store)
    stat = _sample_full_adv_stat(_ADV_OK_A, views=99)

    success_result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_ADV_OK_A)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=_PartialFailureFetcher({_ADV_OK_A: [stat]}),
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )
    assert success_result.full_adv_stats_written == 1
    after_success = await load_read_latest_full_adv_facts(
        store, adv_ids=(_ADV_OK_A,)
    )
    assert len(after_success) == 1
    assert after_success[0].views == 99

    fail_fetcher = _PartialFailureFetcher(
        {_ADV_OK_A: [stat]},
        fail_adv_ids=frozenset({_ADV_OK_A}),
    )
    fail_result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery([_Advert(_ADV_OK_A)]),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fail_fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )
    failed_outcome = next(o for o in fail_result.outcomes if o.adv_id == _ADV_OK_A)
    assert failed_outcome.fact_write_succeeded is False
    assert failed_outcome.availability_reason_code == REASON_COLLECTOR_SOURCE_ERROR
    assert fail_result.full_adv_stats_written == 0

    after_failure = await load_read_latest_full_adv_facts(
        store, adv_ids=(_ADV_OK_A,)
    )
    assert len(after_failure) == 1
    assert after_failure[0].views == 99
    assert after_failure[0].latest_version_num == after_success[0].latest_version_num

    avail_rows = _availability_for_adv(store, _ADV_OK_A)
    assert len(avail_rows) == 2
    assert avail_rows[0]["reason_code"] == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED
    assert avail_rows[1]["reason_code"] == REASON_COLLECTOR_SOURCE_ERROR
    assert avail_rows[0]["route_version"] == avail_rows[1]["route_version"]


@pytest.mark.asyncio
async def test_task_63_integration_append_only_partial_failure_multi_campaign(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """6.3: append-only availability; partial failure; route_version evidence."""
    del forbid_management_and_forbidden_seams
    store = InMemoryShopWideCollectStore()
    writer = _ChFullAdvWriter(store)
    fetcher = _PartialFailureFetcher(
        {
            _ADV_OK_A: [_sample_full_adv_stat(_ADV_OK_A)],
            _ADV_OK_B: [_sample_full_adv_stat(_ADV_OK_B)],
            _ADV_FAIL: [_sample_full_adv_stat(_ADV_FAIL)],
        },
        fail_adv_ids=frozenset({_ADV_FAIL}),
    )

    tick_one = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery(
            [_Advert(_ADV_OK_A), _Advert(_ADV_OK_B), _Advert(_ADV_FAIL)]
        ),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert len(store.availability_rows) == 3
    fail_outcome = next(o for o in tick_one.outcomes if o.adv_id == _ADV_FAIL)
    assert fail_outcome.availability_reason_code == REASON_COLLECTOR_SOURCE_ERROR
    ok_written = [
        o
        for o in tick_one.outcomes
        if o.adv_id in {_ADV_OK_A, _ADV_OK_B} and o.fact_write_succeeded
    ]
    assert len(ok_written) == 2

    route_versions_tick_one = {
        row["adv_id"]: row["route_version"] for row in store.availability_rows
    }
    assert all(version >= 1 for version in route_versions_tick_one.values())

    fail_writer = _FailInsertForAdvWriter(
        writer,
        fail_adv_ids=frozenset({_ADV_OK_B}),
    )
    tick_two = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery(
            [_Advert(_ADV_OK_A), _Advert(_ADV_OK_B), _Advert(_ADV_FAIL)]
        ),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=_PartialFailureFetcher(
            {
                _ADV_OK_A: [_sample_full_adv_stat(_ADV_OK_A, views=11)],
                _ADV_OK_B: [_sample_full_adv_stat(_ADV_OK_B, views=22)],
                _ADV_FAIL: [_sample_full_adv_stat(_ADV_FAIL, views=33)],
            },
            fail_adv_ids=frozenset(),
        ),
        full_adv_stat_writer=fail_writer,
        threshold_dates=7,
        observed_at=_T0,
    )

    assert len(store.availability_rows) == 6
    second_fail = next(
        o for o in tick_two.outcomes if o.adv_id == _ADV_OK_B
    )
    assert second_fail.availability_reason_code == REASON_FACT_WRITE_ERROR
    assert second_fail.fact_write_succeeded is False

    read_latest = await load_read_latest_full_adv_facts(
        store,
        adv_ids=(_ADV_OK_A, _ADV_OK_B, _ADV_FAIL),
    )
    by_adv = {row.adv_id: row for row in read_latest}
    assert by_adv[_ADV_OK_A].views == 11
    assert by_adv[_ADV_OK_B].views == 10
    assert by_adv[_ADV_FAIL].views == 33

    for adv_id in (_ADV_OK_A, _ADV_OK_B, _ADV_FAIL):
        rows = _availability_for_adv(store, adv_id)
        assert len(rows) == 2
        assert all(row["collector_id"] == COLLECTOR_UNMANAGED_FULL_ADV for row in rows)
        assert all(row["route_version"] >= 1 for row in rows)


@pytest.mark.asyncio
async def test_task_63_stale_route_epoch_skips_write_other_campaigns_continue(
    forbid_management_and_forbidden_seams: None,
) -> None:
    """6.3: stale route_version fail-closed; sibling campaign всё ещё пишет fact."""
    del forbid_management_and_forbidden_seams
    store = InMemoryShopWideCollectStore()
    writer = _ChFullAdvWriter(store)
    fetcher = _PartialFailureFetcher(
        {
            _ADV_OK_A: [_sample_full_adv_stat(_ADV_OK_A)],
            _ADV_OK_B: [_sample_full_adv_stat(_ADV_OK_B)],
        }
    )
    stale_reader = _GateStaleRouteReader(
        store,
        InventoryRouteSnapshot(
            adv_id=_ADV_OK_A,
            route=CollectionRoute.MANAGED.value,
            route_version=99,
        ),
    )

    result = await collect_unmanaged_campaign_advertising(
        shop_id=_SHOP_ID,
        loader_complex_advs=(),
        campaigns_discovery=_StubDiscovery(
            [_Advert(_ADV_OK_A), _Advert(_ADV_OK_B)]
        ),
        inventory_client=store,
        availability_client=store,
        full_adv_stat_fetcher=fetcher,
        full_adv_stat_writer=writer,
        threshold_dates=7,
        route_reader=stale_reader,
        observed_at=_T0,
    )

    stale_outcome = next(o for o in result.outcomes if o.adv_id == _ADV_OK_A)
    ok_outcome = next(o for o in result.outcomes if o.adv_id == _ADV_OK_B)
    assert stale_outcome.fact_write_succeeded is False
    assert stale_outcome.availability_reason_code in {
        REASON_ROUTE_EPOCH_STALE,
        REASON_OWNERSHIP_MISMATCH,
    }
    assert ok_outcome.fact_write_succeeded is True
    stale_avail = _availability_for_adv(store, _ADV_OK_A)[-1]
    assert stale_avail["route_version"] == 99
    assert stale_avail["reason_code"] == stale_outcome.availability_reason_code
