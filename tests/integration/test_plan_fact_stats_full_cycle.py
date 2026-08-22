"""Интеграционные тесты для полного цикла план-факта.

Act path opens production ``get_clickhouse_client`` / ``default_db.plan_fact_stats``.
Destructive tests redirect both the plan-fact writer and reader onto the
fixture GuardedClickHouseClient and rewrite ``default_db.*`` →
``test_adv_bot_clickhouse.*`` before the allowlist sees SQL/table names.
"""

from contextlib import ExitStack
from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_advs_stat.data_manager import CommonAdvsStatData
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
import app.modules.shop_runner.service_manager.services.plan_fact_controller.clickhouse_plan_fact_manager as plan_fact_ch_module
import app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader as plan_fact_reader_module
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PLAN_FACT_CH_TS_FORMAT_MSK,
    PlanFactCacheManager,
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = pytest.mark.destructive_local


@pytest.fixture
def plan_fact_ch_on_test_db(
    clickhouse_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect plan-fact CH writer/reader onto fixture Guarded client + rewrite."""
    patch_get_clickhouse_client(
        monkeypatch,
        [plan_fact_ch_module, plan_fact_reader_module],
        clickhouse_client,
    )


def _make_minimal_common_advs_stat_data(adv_setting: object) -> CommonAdvsStatData:
    """Минимальный CommonAdvsStatData для тестов с моками (без обращения к CH/Postgres)."""
    zero_stat = SmallFullAdvStat(
        views=0, clicks=0, spend=0.0, added_to_cart=0, orders=0, sum_price=0.0
    )
    return CommonAdvsStatData(
        adv_setting=adv_setting,
        keywords=[],
        min_orders_per_1000_rub=None,
        hard_min_ctr=None,
        auto_cpm=0,
        auction_cpm=None,
        total_spend=0.0,
        addition_spend_in_adv=0.0,
        all_orders_for_last_days=0,
        mean_orders_for_last_days=0.0,
        mean_price_for_order=1.0,
        spend_for_inner_advs=None,
        full_adv_stat_for_last_days_for_auto_adv=zero_stat,
        full_adv_stat_for_last_days_for_auction=zero_stat,
        common_stat=None,
        sales_predict_method=FactMethods.DIRECT_SALES,
        cost_per_order_from_additional_last_week=None,
    )


def _create_manager(wb_api, redis_client_wrapper):
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)

    wb_manager_hub = MagicMock()
    wb_manager_hub.wb_data_manager = MagicMock()
    wb_manager_hub.wb_manager = MagicMock()

    return CoroutinesManager(
        wb_api,
        redis_client_wrapper,
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=plan_fact_reader,
        wb_manager_hub=wb_manager_hub,
    )


def _pre_adv_from_complex(complex_adv: ComplexAdv, plan_data: PlanData) -> PreComplexAdv:
    """PreComplexAdv для update_plan_fact_stats (путь process_pre_adv)."""
    return PreComplexAdv(
        auto_adv=complex_adv.adv_setting,
        plan_data=plan_data,
        plan_fact_summary=None,
        search_adv=complex_adv.search_adv,
    )


def _mock_pre_adv(adv_id: int, shop_id: str, plan: PlanData) -> PreComplexAdv:
    auto = MagicMock()
    auto.adv_id = adv_id
    cab = MagicMock()
    cab.shop_id = shop_id
    auto.wb_cabinet = cab
    return PreComplexAdv(
        auto_adv=auto,
        plan_data=plan,
        plan_fact_summary=None,
        search_adv=None,
    )


def _enter_pre_adv_mocks(
    stack: ExitStack, manager: CoroutinesManager, pre_advs: list[PreComplexAdv]
) -> None:
    stack.enter_context(
        patch.object(
            manager._wb_shop_data_manager,
            "get_pre_complex_advs",
            new=AsyncMock(return_value=pre_advs),
        )
    )
    stack.enter_context(
        patch(
            "app.modules.wb_adv_updater.phrases_processor.get_good_bad_phrases",
            new=AsyncMock(return_value=[]),
        )
    )
    # plan_fact: факт из Redis keywords → PlanFactProvider (без глобального redis_client).
    stack.enter_context(
        patch(
            "app.modules.shop_runner.required_data_miss.fetch_calculated_keywords_from_redis",
            new=AsyncMock(return_value=[]),
        )
    )
    stack.enter_context(
        patch.object(
            PlanFactProvider,
            "get_stat_data",
            new=AsyncMock(
                return_value=_make_minimal_common_advs_stat_data(MagicMock()),
            ),
        )
    )
    stack.enter_context(
        patch(
            "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.run_tasks",
            new=_run_tasks_sequentially,
        )
    )


async def _run_tasks_sequentially(
    handlers,
    *,
    max_workers: int,
    return_exceptions: bool = True,
    tasks_manager=None,
):
    """Как run_tasks, но без пула — стабильный порядок вызовов моков get_fact_data."""
    del max_workers, tasks_manager
    results: list[object] = []
    for h in handlers:
        try:
            results.append(await h())
        except Exception as exc:
            if return_exceptions:
                results.append(exc)
            else:
                raise
    return results


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_plan_fact_stats(
    clickhouse_client,
    complex_adv,
    access_mock,
    fake_redis,
    plan_fact_ch_on_test_db,
):
    """Тест полного цикла: получение кампаний → получение плана/факта → запись в ClickHouse"""
    del plan_fact_ch_on_test_db
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Настраиваем план и факт для кампании
    plan = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    fact = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    pre_advs = [_pre_adv_from_complex(complex_adv, plan)]
    with ExitStack() as stack:
        _enter_pre_adv_mocks(stack, manager, pre_advs)
        stack.enter_context(
            patch.object(
                PlanFactProvider,
                "get_fact_data",
                return_value=fact,
            )
        )
        # Используем __wrapped__ для обхода декоратора
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что данные записались в ClickHouse
        result = await clickhouse_client.query(
            f"""
            SELECT
                adv_id, shop_id, date, timestamp,
                plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method,
                version
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )

    assert result is not None
    assert len(result.result_rows) == 1

    row = result.result_rows[0]
    assert row[0] == complex_adv.adv_id  # adv_id
    assert row[1] == complex_adv.shop_id  # shop_id из wb_cabinet / ComplexAdv
    assert isinstance(row[2], date)  # date
    assert isinstance(row[3], datetime)  # timestamp
    assert row[4] == 100  # plan_orders
    assert row[5] == 500  # plan_target_pay_for_order
    assert row[6] == 1000  # plan_max_pay_for_order
    assert row[7] == 95.5  # fact_predict_orders
    assert row[8] == 90.0  # fact_original_orders
    assert row[9] == 520.0  # fact_pay_for_order
    assert row[10] == "DIRECT_SALES"  # fact_method
    assert isinstance(row[11], float)  # version

    reader = PlanFactReader(
        cache_manager=PlanFactCacheManager(
            redis_client=RedisClient(redis_client=fake_redis)
        )
    )
    summary = await reader.get_latest_plan_fact(complex_adv.adv_id)
    assert summary is not None
    assert summary.plan_fact_ch_ts_msk is not None
    fmt_res = await clickhouse_client.query(
        """
        SELECT formatDateTime(max(timestamp), %(plan_fact_ts_format)s, 'Europe/Moscow')
        FROM test_adv_bot_clickhouse.plan_fact_stats
        WHERE adv_id = %(adv_id)s
        """,
        parameters={
            "adv_id": complex_adv.adv_id,
            "plan_fact_ts_format": PLAN_FACT_CH_TS_FORMAT_MSK,
        },
    )
    assert fmt_res.result_rows
    assert summary.plan_fact_ch_ts_msk == fmt_res.result_rows[0][0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_with_real_complex_adv(
    clickhouse_client,
    complex_adv,
    access_mock,
    fake_redis,
    plan_fact_ch_on_test_db,
):
    """Тест с реальными ComplexAdv из фикстуры"""
    del plan_fact_ch_on_test_db
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    # Используем реальные данные из complex_adv
    plan = PlanData(orders=200, target_pay_for_order=600, max_pay_for_order=1200)
    fact = FactData(
        predict_orders=190.0,
        original_orders=180.0,
        pay_for_order=610.0,
        fact_method=FactMethods.BY_CARTS,
    )

    pre_advs = [_pre_adv_from_complex(complex_adv, plan)]
    with ExitStack() as stack:
        _enter_pre_adv_mocks(stack, manager, pre_advs)
        stack.enter_context(
            patch.object(
                PlanFactProvider,
                "get_fact_data",
                return_value=fact,
            )
        )
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что данные записались с правильным adv_id из complex_adv
        result = await clickhouse_client.query(
            f"""
            SELECT adv_id, shop_id, plan_orders, fact_predict_orders, fact_method
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            LIMIT 1
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]
    assert row[0] == complex_adv.adv_id
    assert row[1] == complex_adv.shop_id
    assert row[2] == 200
    assert row[3] == 190.0
    assert row[4] == "BY_CARTS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_error_handling_for_some_advs(
    clickhouse_client,
    complex_adv,
    access_mock,
    fake_redis,
    plan_fact_ch_on_test_db,
):
    """Тест обработки ошибок получения данных для отдельных кампаний"""
    del plan_fact_ch_on_test_db
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    plan1 = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    plan2 = PlanData(orders=50, target_pay_for_order=300, max_pay_for_order=800)

    fact1 = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    pre_advs = [
        _pre_adv_from_complex(complex_adv, plan1),
        _mock_pre_adv(99999, "test_shop_2", plan2),
    ]

    with ExitStack() as stack:
        _enter_pre_adv_mocks(stack, manager, pre_advs)
        stack.enter_context(
            patch(
                "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.run_tasks",
                new=_run_tasks_sequentially,
            )
        )
        stack.enter_context(
            patch.object(
                PlanFactProvider,
                "get_fact_data",
                new=AsyncMock(side_effect=[fact1, Exception("Fact data error")]),
            )
        )
        with pytest.raises(Exception, match="Fact data error"):
            await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_multiple_advs_simultaneously(
    clickhouse_client,
    complex_adv,
    access_mock,
    fake_redis,
    plan_fact_ch_on_test_db,
):
    """Тест записи данных для нескольких кампаний одновременно"""
    del plan_fact_ch_on_test_db
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    plans = [
        PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000),
        PlanData(orders=150, target_pay_for_order=550, max_pay_for_order=1100),
        PlanData(orders=200, target_pay_for_order=600, max_pay_for_order=1200),
    ]

    facts = [
        FactData(
            predict_orders=95.5,
            original_orders=90.0,
            pay_for_order=520.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
        FactData(
            predict_orders=145.3,
            original_orders=140.0,
            pay_for_order=560.0,
            fact_method=FactMethods.BY_CARTS,
        ),
        FactData(
            predict_orders=190.0,
            original_orders=180.0,
            pay_for_order=610.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
    ]

    pre_advs = [
        _pre_adv_from_complex(complex_adv, plans[0]),
        _mock_pre_adv(11111, "test_shop_2", plans[1]),
        _mock_pre_adv(22222, "test_shop_3", plans[2]),
    ]

    with ExitStack() as stack:
        _enter_pre_adv_mocks(stack, manager, pre_advs)
        stack.enter_context(
            patch(
                "app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_manager.run_tasks",
                new=_run_tasks_sequentially,
            )
        )
        stack.enter_context(
            patch.object(
                PlanFactProvider,
                "get_fact_data",
                new=AsyncMock(side_effect=facts),
            )
        )
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем, что все три кампании записались
        result = await clickhouse_client.query(
            f"""
            SELECT adv_id, plan_orders, fact_predict_orders, fact_method
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id IN ({complex_adv.adv_id}, 11111, 22222)
            ORDER BY adv_id
            """
        )

    assert len(result.result_rows) == 3

    # Проверяем данные для каждой кампании
    assert result.result_rows[0][0] == complex_adv.adv_id
    assert result.result_rows[0][1] == 100
    assert result.result_rows[0][2] == 95.5
    assert result.result_rows[0][3] == "DIRECT_SALES"

    assert result.result_rows[1][0] == 11111
    assert result.result_rows[1][1] == 150
    assert result.result_rows[1][2] == 145.3
    assert result.result_rows[1][3] == "BY_CARTS"

    assert result.result_rows[2][0] == 22222
    assert result.result_rows[2][1] == 200
    assert result.result_rows[2][2] == 190.0
    assert result.result_rows[2][3] == "DIRECT_SALES"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_data_correctness_in_clickhouse(
    clickhouse_client,
    complex_adv,
    access_mock,
    fake_redis,
    plan_fact_ch_on_test_db,
):
    """Тест корректности данных в ClickHouse после записи"""
    del plan_fact_ch_on_test_db
    await clickhouse_client.command("TRUNCATE TABLE test_adv_bot_clickhouse.plan_fact_stats")

    wb_api = WBApi(access_mock, AsyncMock())
    redis_client_wrapper = RedisClient(redis_client=fake_redis)
    manager = _create_manager(wb_api, redis_client_wrapper)

    plan = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    fact = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    pre_advs = [_pre_adv_from_complex(complex_adv, plan)]
    with ExitStack() as stack:
        _enter_pre_adv_mocks(stack, manager, pre_advs)
        stack.enter_context(
            patch.object(
                PlanFactProvider,
                "get_fact_data",
                return_value=fact,
            )
        )
        await manager.update_plan_fact_stats.__wrapped__(manager)  # noqa
    async with anti_ch_crash_semaphore:
        # Проверяем все поля на корректность
        result = await clickhouse_client.query(
            f"""
            SELECT
                adv_id, shop_id, date, timestamp,
                plan_orders, plan_target_pay_for_order, plan_max_pay_for_order,
                fact_predict_orders, fact_original_orders, fact_pay_for_order, fact_method,
                version
            FROM test_adv_bot_clickhouse.plan_fact_stats
            WHERE adv_id = {complex_adv.adv_id}
            LIMIT 1
            """
        )

    assert len(result.result_rows) == 1
    row = result.result_rows[0]

    # Проверяем обязательные поля
    assert row[0] == complex_adv.adv_id
    assert row[1] == complex_adv.shop_id
    assert isinstance(row[2], date)
    assert isinstance(row[3], datetime)

    # Проверяем план
    assert row[4] == 100
    assert row[5] == 500
    assert row[6] == 1000

    # Проверяем факт
    assert row[7] == 95.5
    assert row[8] == 90.0
    assert row[9] == 520.0
    assert row[10] == "DIRECT_SALES"

    # Проверяем версию
    assert isinstance(row[11], float)
    assert row[11] > 0

    # Проверяем, что timestamp близок к текущему времени
    # ClickHouse возвращает datetime с timezone, нормализуем для сравнения
    timestamp_from_db = row[3].replace(tzinfo=None) if row[3].tzinfo else row[3]
    time_diff = abs((datetime.now() - timestamp_from_db).total_seconds())
    assert time_diff < 60  # Разница должна быть меньше минуты
