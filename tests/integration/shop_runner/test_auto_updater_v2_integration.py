"""Integration/regression tests for AutoUpdater v2 (requires Postgres test DB)."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dependency_injector import providers
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system import (
    AdvControlSystem,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from tests.factories.adv_factory import AdvSettingFactory
from tests.factories.complex_adv import (
    ComplexAdvSeed,
    build_calculated_keywords,
    build_complex_keyword_settings,
    create_complex_adv_seed,
)

pytestmark = pytest.mark.destructive_local
async def _create_second_complex_adv_seed(
    session: AsyncSession, wb_cabinet_id: int
) -> ComplexAdvSeed:
    search_adv = AdvSettingFactory.build(active_status="started")
    search_adv.adv_id = 880_022
    search_adv.cpm = 80

    adv_setting = AdvSettingFactory.build(
        adv_id=880_011,
        wb_cabinet_id=wb_cabinet_id,
        nmids=[990_011],
        auto_update_white_list=True,
        auto_update_target_place=True,
        auto_update_exponent=True,
        auto_add_only_relevant_phrase=False,
        bidder_for_auto=True,
        bidder_active=True,
        bot_active=False,
    )
    adv_setting.cpm = 90
    adv_setting.max_cpm = 220
    adv_setting.max_place = 130
    adv_setting.exponent_predict_ctr = 7.0
    adv_setting._search_adv = search_adv.adv_id

    session.add(adv_setting)
    await session.flush()
    await session.refresh(adv_setting)

    keyword_settings = build_complex_keyword_settings(adv_setting.id)
    session.add_all(keyword_settings)
    await session.flush()
    for ks in keyword_settings:
        await session.refresh(ks)

    calculated_keywords = build_calculated_keywords(adv_setting, keyword_settings)
    return ComplexAdvSeed(
        adv_setting=adv_setting,
        search_adv=search_adv,
        keyword_settings=keyword_settings,
        calculated_keywords=calculated_keywords,
    )


@pytest.mark.asyncio(scope="function")
async def test_adv_control_system_process_adv_does_not_touch_other_adv_keywords(
    postgres_session: AsyncSession,
    app_container,
    fake_redis,
    sm_generator,
) -> None:
    await postgres_session.begin()
    seed_a = await create_complex_adv_seed(postgres_session)
    seed_b = await _create_second_complex_adv_seed(
        postgres_session, seed_a.adv_setting.wb_cabinet_id
    )
    seed_a.adv_setting.bot_active = True
    seed_b.adv_setting.bot_active = True

    before_b = {ks.id: ks.hard_status for ks in seed_b.keyword_settings}

    async def get_keywords_a(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_a.calculated_keywords

    complex_a = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_keywords_a,
        adv_setting=seed_a.adv_setting,
        search_adv=seed_a.search_adv,
    )
    complex_a.get_mean_auto_ctr = AsyncMock(return_value=3.0)

    plan_data = PlanData(
        orders=15, target_pay_for_order=120, max_pay_for_order=300
    )
    fact_data = FactData(
        predict_orders=10.0,
        pay_for_order=500.0,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )

    control = AdvControlSystem(max_last_period=2)

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_fact_data",
            new=AsyncMock(return_value=fact_data),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.ChangePlanFact.check_equal_in_cache",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.sm",
            return_value=sm_generator,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.utils.get_max_cpm",
            new=AsyncMock(return_value=400),
        ),
    ):
        app_container.redis_client.override(providers.Object(fake_redis))
        try:
            await control.process_adv(complex_a, force=3)
        finally:
            app_container.redis_client.reset_override()

    for ks_id, hard_before in before_b.items():
        ks_row = await postgres_session.get(KeywordSetting, ks_id)
        assert ks_row is not None
        assert ks_row.hard_status == hard_before

    updated_a = cast(
        AdvSetting | None,
        await postgres_session.get(AdvSetting, seed_a.adv_setting.id),
    )
    assert updated_a is not None


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
    session.close = MagicMock()
    return session


@pytest.mark.asyncio(scope="function")
async def test_coroutines_manager_adv_settings_auto_update_calls_each_fresh_adv(
    postgres_session: AsyncSession,
    access_mock,
    client_session_mock,
    fake_redis,
    monkeypatch,
) -> None:
    """Smoke: entrypoint schedules one handler per eligible adv when stats cache says fresh."""
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    await postgres_session.begin()
    seed_a = await create_complex_adv_seed(postgres_session)
    seed_b = await _create_second_complex_adv_seed(
        postgres_session, seed_a.adv_setting.wb_cabinet_id
    )
    seed_a.adv_setting.bot_active = True
    seed_b.adv_setting.bot_active = True

    async def get_kw_a(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_a.calculated_keywords

    async def get_kw_b(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_b.calculated_keywords

    adv_a = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_a,
        adv_setting=seed_a.adv_setting,
        search_adv=seed_a.search_adv,
    )
    adv_b = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_b,
        adv_setting=seed_b.adv_setting,
        search_adv=seed_b.search_adv,
    )

    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.shop_runner.modules.wb_api import WBApi
    from app.modules.shop_runner.service_manager import CoroutinesManager
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactReader,
    )
    from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
        StatsFreshnessState,
    )
    from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager

    access_mock.shop_id = "test_shop_id"
    wb_api = WBApi(access_mock, client_session_mock)

    fresh = StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)

    async def _mget(_shop_id: str, adv_ids: list[int]):
        return [(aid, fresh, "hit", None) for aid in adv_ids]

    process_mock = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv_a, adv_b]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.AdvControlSystem.process_adv",
            new=process_mock,
        ),
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=2),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    assert process_mock.await_count == 2


@pytest.mark.asyncio(scope="function")
async def test_adv_settings_auto_update_stats_freshness_gate_skips_stale_hit(
    postgres_session: AsyncSession,
    access_mock,
    client_session_mock,
    fake_redis,
    monkeypatch,
) -> None:
    """Stale (non-emergency) cache hit must not run process_adv; fresh hit still runs."""
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    await postgres_session.begin()
    seed_a = await create_complex_adv_seed(postgres_session)
    seed_b = await _create_second_complex_adv_seed(
        postgres_session, seed_a.adv_setting.wb_cabinet_id
    )
    seed_a.adv_setting.bot_active = True
    seed_b.adv_setting.bot_active = True

    async def get_kw_a(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_a.calculated_keywords

    async def get_kw_b(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_b.calculated_keywords

    adv_a = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_a,
        adv_setting=seed_a.adv_setting,
        search_adv=seed_a.search_adv,
    )
    adv_b = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_b,
        adv_setting=seed_b.adv_setting,
        search_adv=seed_b.search_adv,
    )

    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.shop_runner.modules.wb_api import WBApi
    from app.modules.shop_runner.service_manager import CoroutinesManager
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactReader,
    )
    from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
        StatsFreshnessState,
    )
    from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager

    access_mock.shop_id = "test_shop_id"
    wb_api = WBApi(access_mock, client_session_mock)

    fresh = StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)
    stale = StatsFreshnessState(
        is_fresh=False,
        is_stale_over_6h=False,
        reason="integration stale",
    )

    async def _mget(_shop_id: str, adv_ids: list[int]):
        out: list[tuple[int, StatsFreshnessState, str, str | None]] = []
        for aid in adv_ids:
            if aid == seed_a.adv_setting.adv_id:
                out.append((aid, fresh, "hit", None))
            else:
                out.append((aid, stale, "hit", None))
        return out

    process_mock = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv_a, adv_b]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.AdvControlSystem.process_adv",
            new=process_mock,
        ),
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=2),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    assert process_mock.await_count == 1
    called = process_mock.call_args[0][0]
    assert called.adv_id == seed_a.adv_setting.adv_id


@pytest.mark.parametrize("entry_kind", ["miss", "invalid"])
@pytest.mark.asyncio(scope="function")
async def test_adv_settings_auto_update_stats_freshness_gate_fail_open_on_miss_or_invalid(
    postgres_session: AsyncSession,
    access_mock,
    client_session_mock,
    fake_redis,
    monkeypatch,
    entry_kind: str,
) -> None:
    """Cache miss / invalid payload kinds must fail-open and still invoke process_adv."""
    monkeypatch.setenv("AUTO_SETTING_ACTIVE", "true")
    await postgres_session.begin()
    seed_a = await create_complex_adv_seed(postgres_session)
    seed_b = await _create_second_complex_adv_seed(
        postgres_session, seed_a.adv_setting.wb_cabinet_id
    )
    seed_a.adv_setting.bot_active = True
    seed_b.adv_setting.bot_active = True

    async def get_kw_a(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_a.calculated_keywords

    async def get_kw_b(
        _: ComplexAdv,
        *,
        cache_only: bool = True,
    ):
        return seed_b.calculated_keywords

    adv_a = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_a,
        adv_setting=seed_a.adv_setting,
        search_adv=seed_a.search_adv,
    )
    adv_b = ComplexAdv(
        shop_id="test_shop_id",
        get_keywords_func=get_kw_b,
        adv_setting=seed_b.adv_setting,
        search_adv=seed_b.search_adv,
    )

    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.shop_runner.modules.wb_api import WBApi
    from app.modules.shop_runner.service_manager import CoroutinesManager
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactReader,
    )
    from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager

    access_mock.shop_id = "test_shop_id"
    wb_api = WBApi(access_mock, client_session_mock)

    async def _mget(_shop_id: str, adv_ids: list[int]):
        return [(aid, None, entry_kind, None) for aid in adv_ids]

    process_mock = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_complex_advs",
            new=AsyncMock(return_value=[adv_a, adv_b]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.adv_control_system.AdvControlSystem.process_adv",
            new=process_mock,
        ),
    ):
        manager = CoroutinesManager(
            wb_api,
            RedisClient(redis_client=fake_redis),
            tasks_manager=TasksManager(max_workers=2),
            plan_fact_reader=MagicMock(spec=PlanFactReader),
            wb_manager_hub=MagicMock(),
        )
        manager._redis_stats_freshness_cache.mget_entries = AsyncMock(side_effect=_mget)
        await manager.adv_settings_auto_update.__wrapped__(manager)

    assert process_mock.await_count == 2
