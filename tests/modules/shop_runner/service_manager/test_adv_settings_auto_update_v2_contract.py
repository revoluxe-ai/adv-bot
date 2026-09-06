"""Contract tests for ``adv_settings_auto_update`` (v3-only entrypoint).

Call chain (``CoroutinesManager.adv_settings_auto_update`` → ``process_adv_v3``):

1. ``settings.AUTO_SETTING_ACTIVE`` gate
2. ``WBShopDataManager.get_complex_advs(load_extras=False)``
3. Filters: ``bot_active``, ``is_part_auto_setting_active``, ``search_adv_active_status``
4. A/B Hold pipeline (``process_ab_setup`` / ``process_ab_hold``) + ordinary ``process_adv_v3``
5. ``run_tasks`` per handler
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager

pytestmark = pytest.mark.unit


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
    session.close = MagicMock()
    return session


def _search_adv_started() -> MagicMock:
    s = MagicMock(spec=AdvSetting)
    s.adv_id = 90001
    s.active_status = "started"
    s.cpm = 90
    return s


def _configure_adv_for_auto_pipeline(adv_setting_mock: MagicMock) -> None:
    """Минимальная конфигурация AdvSetting mock для adv_settings_auto_update."""
    adv_setting_mock.bot_active = True
    adv_setting_mock.auto_update_white_list = True
    adv_setting_mock.auto_update_target_place = True
    adv_setting_mock.auto_update_exponent = False
    adv_setting_mock.individual_keywords_target_place_mode = False
    adv_setting_mock.active_status = "started"
    adv_setting_mock.card_ab_hold_mode = "off"


_configure_adv_for_v2_pipeline = _configure_adv_for_auto_pipeline


def _make_complex_adv(
    wb_api: WBApi,
    adv_setting_mock: MagicMock,
    keywords_mocks: list,
    *,
    search_adv: AdvSetting | MagicMock | None,
) -> ComplexAdv:
    async def _get_keywords(_: ComplexAdv, cache_only: bool = False):
        return keywords_mocks

    return ComplexAdv(
        shop_id=wb_api.shop_id,
        adv_setting=adv_setting_mock,
        search_adv=search_adv,
        get_keywords_func=_get_keywords,
    )


def test_max_workers_for_caps_and_minimum():
    assert CoroutinesManager._max_workers_for(0, cap=16) == 1
    assert CoroutinesManager._max_workers_for(1, cap=16) == 1
    assert CoroutinesManager._max_workers_for(10, cap=16) == 10
    assert CoroutinesManager._max_workers_for(100, cap=16) == 16


@pytest.mark.asyncio
async def test_adv_settings_auto_update_returns_early_when_auto_setting_disabled(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "false")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock()
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_not_called()
    manager._redis_stats_freshness_cache.mget_entries.assert_not_called()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_skips_when_no_complex_advs(
    monkeypatch,
    access_mock,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    wb_api = WBApi(access_mock, client_session_mock)
    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock()
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_not_called()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_filters_bot_inactive(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    adv_setting_mock.bot_active = False
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock()
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_not_called()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_filters_when_part_auto_setting_inactive(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    adv_setting_mock.auto_update_white_list = False
    adv_setting_mock.auto_update_target_place = False
    adv_setting_mock.individual_keywords_target_place_mode = False
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock()
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_not_called()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_filters_when_search_adv_not_started(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    search = _search_adv_started()
    search.active_status = "paused"
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=search)

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock()
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_not_called()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_stats_freshness_hit_miss_fail_open(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    """miss / invalid cache entries are fail-open (adv still processed)."""
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(adv_ids[0], None, "miss", None)]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget_entries)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_called_once()
    assert run_tasks_mock.call_args.kwargs["return_exceptions"] is False


@pytest.mark.asyncio
async def test_adv_settings_auto_update_stats_freshness_invalid_payload_fail_open(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(adv_ids[0], None, "invalid", None)]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget_entries)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_called_once()


@pytest.mark.asyncio
async def test_adv_settings_auto_update_stats_freshness_stale_over_6h_still_runs_v3(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    emergency = StatsFreshnessState(
        is_fresh=False,
        is_stale_over_6h=True,
        reason="too old",
    )

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(adv_ids[0], emergency, "hit", None)]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget_entries)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_called_once()
    handlers = run_tasks_mock.call_args.args[0]
    assert len(handlers) == 1
    assert callable(handlers[0])


@pytest.mark.asyncio
async def test_adv_settings_auto_update_stats_freshness_stale_still_runs_v3(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())

    stale = StatsFreshnessState(
        is_fresh=False,
        is_stale_over_6h=False,
        reason="cluster stale",
    )

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(adv_ids[0], stale, "hit", None)]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget_entries)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_called_once()
    handlers = run_tasks_mock.call_args.args[0]
    assert len(handlers) == 1


@pytest.mark.asyncio
async def test_adv_settings_auto_update_run_tasks_max_workers_matches_handler_count(
    monkeypatch,
    access_mock,
    adv_setting_mock,
    keywords_mocks,
    client_session_mock,
    fake_redis,
):
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    access_mock.shop_id = "shop-contract"
    _configure_adv_for_v2_pipeline(adv_setting_mock)
    wb_api = WBApi(access_mock, client_session_mock)
    adv1 = _make_complex_adv(wb_api, adv_setting_mock, keywords_mocks, search_adv=_search_adv_started())
    adv2_mock = MagicMock(spec=AdvSetting)
    for attr, val in [
        ("adv_id", 25040170),
        ("nmids", [222811119]),
        ("search_adv_id", None),
        ("active_status", "started"),
        ("bot_active", True),
        ("auto_update_white_list", True),
        ("auto_update_target_place", True),
        ("auto_update_exponent", False),
        ("individual_keywords_target_place_mode", False),
        ("plan_for_sales_for_day", 10),
        ("target_price_for_order", 100),
        ("max_price_for_order", 250),
    ]:
        setattr(adv2_mock, attr, val)
    adv2 = _make_complex_adv(wb_api, adv2_mock, keywords_mocks, search_adv=_search_adv_started())

    fresh = StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)

    async def _mget_entries(_shop_id: str, adv_ids: list[int]):
        return [(aid, fresh, "hit", None) for aid in adv_ids]

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv1, adv2]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.run_tasks",
            new=AsyncMock(return_value=[None, None]),
        ) as run_tasks_mock,
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=1),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget_entries)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    run_tasks_mock.assert_called_once()
    kwargs = run_tasks_mock.call_args.kwargs
    assert kwargs["max_workers"] == 2
    assert kwargs["return_exceptions"] is False
    handlers = run_tasks_mock.call_args.args[0]
    assert len(handlers) == 2