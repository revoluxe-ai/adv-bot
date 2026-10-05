"""Shop-runner orchestration entry — задачи 8.2 (S01) и 8.3 (S20).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

S01: periodic ``WBShop.run`` initiates discovery + dual-path без scripts/Job.
S20: один tick discover → route → inventory → managed + unmanaged → availability;
no duplicate declared fact grains; no management writes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats, FullAdvStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.shop_wide_collection.managed_record_contract import (
    MANAGED_RECORD_COROUTINE_NAMES,
    SHOP_WIDE_UNMANAGED_COROUTINE_NAME,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CollectionRoute,
)
from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    COLLECTOR_UNMANAGED_FULL_ADV,
    REASON_UNMANAGED_FACT_WRITE_SUCCEEDED,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop

_SHOP_ID = "shop-wide-tick-8x"
_MANAGED_ADV_ID = 101
_SEARCH_ADV_ID = 202
_WB_ONLY_ADV_ID = 999_001
_REPO = Path(__file__).resolve().parents[3]


class _FakeTaskGroup:
    """TaskGroup, который фиксирует create_task и не исполняет корутины."""

    def __init__(self) -> None:
        self.created: list[Any] = []

    async def __aenter__(self) -> _FakeTaskGroup:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def create_task(self, coro: Any) -> MagicMock:
        self.created.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()
        return MagicMock()


class _Nm:
    def __init__(self, nm_id: int) -> None:
        self.nm_id = nm_id


class _Advert:
    def __init__(
        self,
        adv_id: int,
        status: int = 9,
        nm_ids: tuple[int, ...] = (555,),
    ) -> None:
        self.id = adv_id
        self.status = status
        self.nm_settings: tuple[_Nm, ...] = tuple(_Nm(n) for n in nm_ids)


class _QueryRowsResult:
    def __init__(self, result_rows: Sequence[Sequence[object]]) -> None:
        self.result_rows = result_rows


class InMemoryShopWideClickHouse:
    """Inventory + availability на одном injected CH клиенте."""

    def __init__(self) -> None:
        self.inventory_rows: list[dict[str, object]] = []
        self.availability_rows: list[dict[str, object]] = []

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRowsResult:
        params = dict(parameters or {})
        stripped = query.strip()
        if stripped.startswith("SELECT") and "shop_campaign_inventory" in query:
            return _QueryRowsResult(self._select_inventory(query, params))
        if stripped.startswith("INSERT INTO default_db.shop_campaign_inventory"):
            self.inventory_rows.append(dict(params))
            return _QueryRowsResult(())
        if stripped.startswith(
            "INSERT INTO default_db.shop_campaign_collection_availability"
        ):
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
        adv_ids = set(int(x) for x in params["adv_ids"])  # type: ignore[arg-type]
        latest: dict[int, dict[str, object]] = {}
        for row in self.inventory_rows:
            adv_id = int(row["adv_id"])  # type: ignore[arg-type]
            if row["shop_id"] != shop_id or adv_id not in adv_ids:
                continue
            current = latest.get(adv_id)
            if current is None or int(row["version"]) >= int(current["version"]):  # type: ignore[arg-type]
                latest[adv_id] = row
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
        adv_ids = set(int(x) for x in params["adv_ids"])  # type: ignore[arg-type]
        latest: dict[int, dict[str, object]] = {}
        for row in self.inventory_rows:
            adv_id = int(row["adv_id"])  # type: ignore[arg-type]
            if row["shop_id"] != shop_id or adv_id not in adv_ids:
                continue
            current = latest.get(adv_id)
            if current is None or int(row["version"]) >= int(current["version"]):  # type: ignore[arg-type]
                latest[adv_id] = row
        return [
            (row["adv_id"], row["route"], row["route_version"])
            for row in latest.values()
        ]


def _setting(
    *,
    adv_id: int,
    nmids: list[int],
    active_status: str,
    bot_active: bool,
    setting_id: int,
    search_adv_id: int | None = None,
) -> MagicMock:
    row = MagicMock(spec=AdvSetting)
    row.adv_id = adv_id
    row.id = setting_id
    row.nmids = list(nmids)
    row.active_status = active_status
    row.bot_active = bot_active
    row.search_adv_id = search_adv_id
    row.plan_for_sales_for_day = None
    row.target_price_for_order = None
    row.max_price_for_order = None
    return row


def _managed_loader_adv() -> ComplexAdv:
    parent = _setting(
        adv_id=_MANAGED_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=1,
        search_adv_id=_SEARCH_ADV_ID,
    )
    search = _setting(
        adv_id=_SEARCH_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=2,
    )
    return ComplexAdv(
        shop_id=_SHOP_ID,
        adv_setting=parent,
        search_adv=search,
        target_pay_for_order=None,
    )


def _enable_shop_wide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_ENABLED", "1")
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_SHOP_IDS", _SHOP_ID)


def _forbidden(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("forbidden management or scripts/Job side effect")


@pytest.fixture
def forbid_management_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Падает при management writes и scripts/Job primary executor."""
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbidden,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.ApplyManager",
        _forbidden,
    )
    scripts_dir = _REPO / "scripts"
    assert not (scripts_dir / "collect_shop_wide_adv.py").exists()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("dual_path_enabled", [False, True])
async def test_task_82_s01_periodic_tick_initiates_dual_path_without_scripts_job(
    monkeypatch: pytest.MonkeyPatch,
    dual_path_enabled: bool,
) -> None:
    """8.2 / S01: ``WBShop.run`` ставит managed RECORD и shop-wide tick в shop-runner.

    OFF — managed-only без unmanaged coroutine. ON — dual-path task в
    ``CoroutinesManager``, без delegate to scripts/Job.
    """
    if dual_path_enabled:
        _enable_shop_wide(monkeypatch)
    else:
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_ENABLED", raising=False)
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_SHOP_IDS", raising=False)

    wb_api = MagicMock(spec=WBApi)
    wb_api.shop_id = _SHOP_ID
    redis_manager = MagicMock(spec=RedisShopManager)
    redis_manager.DEFAULT_TTL = 60
    shop = WBShop(
        wb_api,
        redis_manager,
        RedisClient(redis_client=MagicMock()),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=MagicMock(),
        wb_manager_hub=MagicMock(),
    )
    shop._alive_worker_run = MagicMock(return_value=None)  # type: ignore[method-assign]

    with (
        patch("app.modules.shop_runner.wb_shop.CoroutinesManager") as manager_cls,
        patch("asyncio.TaskGroup", new=_FakeTaskGroup),
    ):
        await shop.run()

    instance = manager_cls.return_value
    for name in MANAGED_RECORD_COROUTINE_NAMES:
        call = getattr(instance, name).call_args
        assert call is not None, name
        assert call.kwargs["only_bot_active"] is False

    unmanaged_call = getattr(instance, SHOP_WIDE_UNMANAGED_COROUTINE_NAME).call_args
    if dual_path_enabled:
        assert unmanaged_call is not None
    else:
        assert unmanaged_call is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_83_s20_full_tick_discover_route_inventory_dual_collect(
    monkeypatch: pytest.MonkeyPatch,
    forbid_management_writes: None,
    access_mock: Any,
    fake_redis: Any,
) -> None:
    """8.3 / S20: один tick — discover→route→inventory→managed+unmanaged→availability.

    Managed id не попадает в unmanaged eligible; WB-only id пишет full_adv один раз;
    availability фиксирует outcomes; management writes forbidden.
    """
    del forbid_management_writes
    _enable_shop_wide(monkeypatch)

    loader_adv = _managed_loader_adv()
    ch = InMemoryShopWideClickHouse()
    managed_full_ids: set[int] = set()
    unmanaged_written_adv_ids: set[int] = set()
    captured: dict[str, Any] = {}

    async def _managed_full_fetch(
        _data_manager: Any,
        adv_ids: set[int] | list[int],
        threshold_dates: Any = None,
    ) -> list[Any]:
        managed_full_ids.update(int(x) for x in adv_ids)
        _ = threshold_dates
        return []

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

    async def _unmanaged_full_fetch(
        adv_ids: set[int],
        threshold_dates: int,
    ) -> list[FullAdvStat]:
        assert len(adv_ids) == 1
        adv_id = next(iter(adv_ids))
        assert adv_id == _WB_ONLY_ADV_ID
        unmanaged_written_adv_ids.add(adv_id)
        _ = threshold_dates
        return [_sample_full_adv_stat(adv_id)]

    discovery_items = [
        _Advert(_MANAGED_ADV_ID),
        _Advert(_SEARCH_ADV_ID),
        _Advert(_WB_ONLY_ADV_ID),
    ]

    class _Discovery:
        async def get_all_campaigns(self) -> list[_Advert]:
            return discovery_items

    access_mock.shop_id = _SHOP_ID
    access_mock.wb_cabinet.shop_id = _SHOP_ID
    wb_api = WBApi(access_mock, MagicMock())
    hub = MagicMock()
    hub.wb_data_manager = MagicMock()
    hub.wb_data_manager.promotion_manager = MagicMock()

    manager = CoroutinesManager(
        wb_api,
        RedisClient(redis_client=fake_redis),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=MagicMock(),
        wb_manager_hub=hub,
    )

    async def _get_complex_advs(**kwargs: Any) -> list[ComplexAdv]:
        assert kwargs["only_bot_active"] is False
        return [loader_adv]

    manager._wb_shop_data_manager.get_complex_advs = _get_complex_advs  # type: ignore[method-assign]

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.wb_data_getter.get_full_adv_stat_for_adv_ids",
        _managed_full_fetch,
    )

    async def _run_tick(**kwargs: Any) -> Any:
        assert kwargs["shop_id"] == _SHOP_ID
        assert len(kwargs["loader_complex_advs"]) == 1
        from app.modules.shop_runner.shop_wide_collection.unmanaged_orchestrator import (
            collect_unmanaged_campaign_advertising,
        )

        result = await collect_unmanaged_campaign_advertising(
            shop_id=kwargs["shop_id"],
            loader_complex_advs=kwargs["loader_complex_advs"],
            campaigns_discovery=_Discovery(),
            inventory_client=ch,
            availability_client=ch,
            full_adv_stat_fetcher=SimpleNamespace(
                get_full_adv_stat_for_adv_ids=_unmanaged_full_fetch
            ),
            full_adv_stat_writer=SimpleNamespace(
                insert=AsyncMock(return_value=None)
            ),
            threshold_dates=7,
        )
        captured["result"] = result
        return result

    monkeypatch.setattr(
        "app.modules.shop_runner.shop_wide_collection.tick_wiring.run_shop_wide_unmanaged_tick",
        _run_tick,
    )

    await manager.update_full_adv_stat.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=False
    )
    _ = await manager.collect_shop_wide_campaign_advertising.__wrapped__(  # type: ignore[attr-defined]
        manager
    )

    result = captured["result"]

    assert result.wb_discovered_count == 3
    assert len(ch.inventory_rows) >= 3
    assert _WB_ONLY_ADV_ID in result.unmanaged_eligible_adv_ids
    assert _MANAGED_ADV_ID not in result.unmanaged_eligible_adv_ids
    assert _SEARCH_ADV_ID not in result.unmanaged_eligible_adv_ids

    managed_decision = result.route_result.decision_for(
        _MANAGED_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    wb_only_decision = result.route_result.decision_for(
        _WB_ONLY_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT
    )
    assert managed_decision is not None
    assert wb_only_decision is not None
    assert managed_decision.route is CollectionRoute.MANAGED
    assert wb_only_decision.route is CollectionRoute.UNMANAGED

    assert loader_adv.all_adv_ids <= managed_full_ids
    assert _WB_ONLY_ADV_ID not in managed_full_ids
    assert unmanaged_written_adv_ids == {_WB_ONLY_ADV_ID}

    wb_only_outcomes = [
        o for o in result.outcomes if o.adv_id == _WB_ONLY_ADV_ID
    ]
    assert len(wb_only_outcomes) == 1
    assert wb_only_outcomes[0].fact_write_succeeded is True
    assert (
        wb_only_outcomes[0].availability_reason_code
        == REASON_UNMANAGED_FACT_WRITE_SUCCEEDED
    )

    assert any(
        row["adv_id"] == _WB_ONLY_ADV_ID
        and row["collector_id"] == COLLECTOR_UNMANAGED_FULL_ADV
        for row in ch.availability_rows
    )

    duplicate_managed = [
        o
        for o in result.outcomes
        if o.adv_id in loader_adv.all_adv_ids and o.fact_write_attempted
    ]
    assert duplicate_managed == []
