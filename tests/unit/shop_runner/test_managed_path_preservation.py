"""Managed path preservation — задачи 5.1–5.3 (LEGACY_BASELINE → TARGET_REGRESSION).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Парные тесты: legacy RECORD collectors на loader universe §B.1 и target
regression через resolver/write-gate без large refactor collectors.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.shop_wide_collection.managed_record_contract import (
    MANAGED_RECORD_COROUTINE_NAMES,
    managed_complex_advs_loader_kwargs,
)
from app.modules.shop_runner.shop_wide_collection.route_resolver import (
    CampaignCollectionGrain,
    CampaignCollectionRouteResolver,
    CollectionRoute,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop

_SHOP_ID = "shop-managed-path-5x"
_PARENT_ADV_ID = 101
_SEARCH_ADV_ID = 202
_WB_ONLY_ADV_ID = 999_001


class _FakeTaskGroup:
    """TaskGroup, который только фиксирует create_task и не исполняет корутины."""

    def __init__(self) -> None:
        self.created: list[Any] = []

    async def __aenter__(self) -> _FakeTaskGroup:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def create_task(self, coro: Any) -> MagicMock:
        """Сохранить аргумент create_task. Реальный цикл shop-runner здесь не идёт."""
        self.created.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()
        return MagicMock()


class _RecordingClustersUpdater:
    """Тонкий конец clusters: запоминает ComplexAdv из loader universe."""

    def __init__(self) -> None:
        self.today: list[list[ComplexAdv]] = []
        self.history: list[tuple[list[ComplexAdv], int]] = []

    async def update_today_stats(
        self, complex_advs: list[ComplexAdv]
    ) -> list[int]:
        """Принять сегодняшний universe без CH write."""
        self.today.append(list(complex_advs))
        return []

    async def update_past_days_stats(
        self, complex_advs: list[ComplexAdv], for_last_days: int
    ) -> None:
        """Принять history universe без CH write."""
        self.history.append((list(complex_advs), for_last_days))


class _RecordingCommonUpdater:
    """Тонкий конец common stat: запоминает ComplexAdv до funnel write."""

    def __init__(self) -> None:
        self.batches: list[list[ComplexAdv]] = []

    async def update_last_week_stats(self, advs: list[ComplexAdv]) -> list[int]:
        """Принять nmid-universe loader'а без funnel write."""
        self.batches.append(list(advs))
        return []


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


def _refused_loader_adv() -> ComplexAdv:
    """Refused parent + search leg — типичный §B.1 loader universe."""
    parent = _setting(
        adv_id=_PARENT_ADV_ID,
        nmids=[555],
        active_status="refused",
        bot_active=False,
        setting_id=1,
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


def _create_manager(access_mock: Any, fake_redis: Any) -> CoroutinesManager:
    """CoroutinesManager с подменённым hub: PG/WB/CH наружу не ходят."""
    access_mock.shop_id = _SHOP_ID
    access_mock.wb_cabinet.shop_id = _SHOP_ID
    from app.modules.shop_runner.modules.wb_api import WBApi as WbApiCls

    wb_api = WbApiCls(access_mock, MagicMock())
    hub = MagicMock()
    hub.wb_data_manager = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    plan_fact_reader = MagicMock()
    plan_fact_reader.get_latest_plan_fact = MagicMock()
    return CoroutinesManager(
        wb_api,
        RedisClient(redis_client=fake_redis),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=plan_fact_reader,
        wb_manager_hub=hub,
    )


async def _run_managed_record_collectors(
    manager: CoroutinesManager,
    loader_adv: ComplexAdv,
    monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
    """LEGACY_BASELINE trace: RECORD bodies через production id-сбор.

    ``get_complex_advs`` — единственный вход universe. Thin ends подменены,
    чтобы не писать CH/WB. ``__wrapped__`` снимает бесконечный ``while_coroutine``.
    """
    loader_kwargs = managed_complex_advs_loader_kwargs()
    clusters = _RecordingClustersUpdater()
    common = _RecordingCommonUpdater()
    full_ids: set[int] = set()
    loader_calls: list[dict[str, bool]] = []

    async def _get_full_adv_stat(
        _data_manager: Any,
        adv_ids: set[int] | list[int],
        threshold_dates: Any = None,
    ) -> list[Any]:
        full_ids.update(int(adv_id) for adv_id in adv_ids)
        _ = threshold_dates
        return []

    async def _get_complex_advs(**kwargs: Any) -> list[ComplexAdv]:
        loader_calls.append(dict(kwargs))
        assert kwargs == loader_kwargs
        return [loader_adv]

    manager._wb_shop_data_manager.get_complex_advs = _get_complex_advs  # type: ignore[method-assign]
    manager._wb_shop_data_manager.wb_only_discovered_ids = {_WB_ONLY_ADV_ID}  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.wb_data_getter.get_full_adv_stat_for_adv_ids",
        _get_full_adv_stat,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.manager.ClustersAdvStatUpdaterContainer",
        lambda **_kwargs: SimpleNamespace(
            clusters_adv_stat_updater=lambda: clusters
        ),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.common_sale_stat_updater.CommonSaleStatUpdaterContainer",
        lambda **_kwargs: SimpleNamespace(
            common_sale_stat_updater=lambda: common
        ),
    )

    only_false = loader_kwargs["only_bot_active"]
    await manager.update_full_adv_stat.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=only_false
    )
    await manager.update_common_sale_stat.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=only_false
    )
    await manager.update_clusters_adv_stats_today.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=only_false
    )
    await manager.update_clusters_adv_stats_history.__wrapped__(  # type: ignore[attr-defined]
        manager, only_bot_active=only_false
    )

    return SimpleNamespace(
        full_ids=full_ids,
        common_batches=common.batches,
        clusters_today=clusters.today,
        clusters_history=clusters.history,
        loader_ids=set(loader_adv.all_adv_ids),
        loader_calls=loader_calls,
    )


def _ids_of(advs: list[ComplexAdv]) -> set[int]:
    """Собрать ``all_adv_ids`` пачки, переданной collector в thin end."""
    found: set[int] = set()
    for adv in advs:
        found.update(int(adv_id) for adv_id in adv.all_adv_ids)
    return found


def _resolver_for_loader(
    loader_adv: ComplexAdv,
    *,
    extra_discovered: set[int] | None = None,
) -> CampaignCollectionRouteResolver:
    """TARGET_REGRESSION helper: resolver на том же loader universe."""
    discovered = set(loader_adv.all_adv_ids)
    if extra_discovered:
        discovered |= extra_discovered
    return CampaignCollectionRouteResolver.from_loader_and_discovery(
        shop_id=_SHOP_ID,
        wb_discovered_adv_ids=discovered | {_WB_ONLY_ADV_ID},
        loader_complex_advs=[loader_adv],
    )


@pytest.mark.unit
def test_task_51_managed_record_contract_matches_loader_ownership() -> None:
    """5.1: managed RECORD contract — §B.1 loader kwargs и coroutine names."""
    kwargs = managed_complex_advs_loader_kwargs()
    assert kwargs["only_bot_active"] is False
    assert kwargs["load_extras"] is False
    assert MANAGED_RECORD_COROUTINE_NAMES == (
        "update_common_sale_stat",
        "update_full_adv_stat",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_51_record_collectors_use_loader_universe_only(
    access_mock: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5.1: legacy RECORD без refactor — universe только из loader §B.1.

    ``refused`` с ``bot_active=False`` остаётся; WB-only id не попадает в collectors.
    """
    loader_adv = _refused_loader_adv()
    assert loader_adv.bot_active is False
    manager = _create_manager(access_mock, fake_redis)
    trace = await _run_managed_record_collectors(manager, loader_adv, monkeypatch)

    assert len(trace.loader_calls) == 4
    assert all(call == managed_complex_advs_loader_kwargs() for call in trace.loader_calls)
    assert trace.loader_ids == {_PARENT_ADV_ID, _SEARCH_ADV_ID}
    assert _WB_ONLY_ADV_ID not in trace.loader_ids
    assert trace.full_ids == trace.loader_ids
    assert len(trace.common_batches) == 1
    assert trace.common_batches[0][0] is loader_adv
    assert len(trace.clusters_today) == 1
    assert trace.clusters_today[0][0] is loader_adv
    assert len(trace.clusters_history) == 1
    assert trace.clusters_history[0][0][0] is loader_adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_52_s14_refused_managed_clusters_no_unmanaged_full_adv_duplicate(
    access_mock: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5.2 / S14: refused → legacy clusters **MAY** run; unmanaged blocked on full_adv.

    LEGACY_BASELINE: ``update_clusters_adv_stats_*`` получают refused ComplexAdv.
    TARGET_REGRESSION: resolver + write eligibility — MANAGED full_adv, no UNMANAGED dup.
    """
    loader_adv = _refused_loader_adv()
    trace = await _run_managed_record_collectors(
        _create_manager(access_mock, fake_redis), loader_adv, monkeypatch
    )

    assert loader_adv._adv_setting.active_status == "refused"
    assert _ids_of(trace.clusters_today[0]) == trace.loader_ids
    assert _ids_of(trace.clusters_history[0][0]) == trace.loader_ids
    assert trace.clusters_history[0][1] == 365

    result = _resolver_for_loader(loader_adv)
    for adv_id in trace.loader_ids:
        full_decision = result.decision_for(
            adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT
        )
        clusters_decision = result.decision_for(
            adv_id, CampaignCollectionGrain.CLUSTERS_ADV_STATS
        )
        assert full_decision is not None
        assert clusters_decision is not None
        assert full_decision.route is CollectionRoute.MANAGED
        assert clusters_decision.route is CollectionRoute.MANAGED
        assert CampaignCollectionRouteResolver.is_managed_collector_write_eligible(
            full_decision
        )
        assert not CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(
            full_decision
        )

    wb_only = result.decision_for(_WB_ONLY_ADV_ID, CampaignCollectionGrain.FULL_ADV_WB_STAT)
    assert wb_only is not None
    assert wb_only.route is CollectionRoute.UNMANAGED
    assert CampaignCollectionRouteResolver.is_unmanaged_collector_write_eligible(wb_only)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("shop_wide_enabled", [False, True])
async def test_task_53_paired_baseline_target_flag_preserves_managed_tick(
    monkeypatch: pytest.MonkeyPatch,
    shop_wide_enabled: bool,
    access_mock: Any,
    fake_redis: Any,
) -> None:
    """5.3 LEGACY_BASELINE → TARGET_REGRESSION: flag OFF/ON — тот же managed RECORD tick.

    OFF — prior managed-only. ON (DUAL_PATH_ACTIVE) не подменяет RECORD coroutines
    и добавляет shop-wide unmanaged task в shop-runner.
    """
    if shop_wide_enabled:
        monkeypatch.setenv("SHOP_WIDE_COLLECTION_ENABLED", "1")
        monkeypatch.setenv("SHOP_WIDE_COLLECTION_SHOP_IDS", _SHOP_ID)
    else:
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_ENABLED", raising=False)
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_SHOP_IDS", raising=False)

    loader_adv = _refused_loader_adv()
    baseline = await _run_managed_record_collectors(
        _create_manager(access_mock, fake_redis),
        loader_adv,
        monkeypatch,
    )
    result = _resolver_for_loader(loader_adv)
    for adv_id in baseline.loader_ids:
        decision = result.decision_for(adv_id, CampaignCollectionGrain.FULL_ADV_WB_STAT)
        assert decision is not None
        assert decision.route is CollectionRoute.MANAGED

    wb_api = MagicMock(spec=WBApi)
    wb_api.shop_id = _SHOP_ID
    redis_manager = MagicMock(spec=RedisShopManager)
    redis_manager.DEFAULT_TTL = 60
    shop = WBShop(
        wb_api,
        redis_manager,
        RedisClient(redis_client=fake_redis),
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

    shop_wide_call = getattr(
        instance, "collect_shop_wide_campaign_advertising"
    ).call_args
    if shop_wide_enabled:
        assert shop_wide_call is not None
    else:
        assert shop_wide_call is None
    assert baseline.full_ids == baseline.loader_ids
