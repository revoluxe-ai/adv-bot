"""Тесты для AdvControlSystem.process_adv"""


from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system import (
    AdvControlSystem,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods

pytestmark = pytest.mark.unit


@pytest.fixture
def plan_data_mock():
    """Фикстура для создания данных плана"""
    return PlanData(
        orders=10,
        target_pay_for_order=100,
        max_pay_for_order=250,
    )


@pytest.fixture
def fact_data_mock():
    """Фикстура для создания данных факта"""
    return FactData(
        predict_orders=8.5,
        pay_for_order=150.0,
        original_orders=8,
        fact_method=FactMethods.DIRECT_SALES,
    )


@pytest.mark.asyncio
async def test_process_adv_no_plan(complex_adv_mock):
    """Тест: план не установлен, функция должна завершиться без выполнения"""
    control_system = AdvControlSystem(max_last_period=2)

    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
        return_value=None,
    ):
        # Не должно быть исключений, функция просто завершается
        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что get_keywords был вызван
        complex_adv_mock.get_keywords.assert_called_once()


@pytest.mark.asyncio
async def test_process_adv_uses_promo_effective_plan_for_state(complex_adv_mock):
    """Состояние определяется по promo-overlay, а не по базовому max CPO."""
    control_system = AdvControlSystem(max_last_period=2)
    adv = complex_adv_mock.adv_setting
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 50
    adv.max_price_for_order = 100
    adv.raise_plan_on_promobonuses = True
    complex_adv_mock.promo_fraction = Decimal("0.5")

    base_plan = PlanData(orders=10, target_pay_for_order=50, max_pay_for_order=100)
    fact = FactData(
        predict_orders=10,
        pay_for_order=150,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )
    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact)
    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ) as mock_updater_class,
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        mock_updater_class.get_plan_data.return_value = base_plan
        control_system.planner.run_for_state = AsyncMock()
        await control_system.process_adv(complex_adv_mock)

    checked_plan = mock_change_plan_fact.check_equal_in_cache.call_args.args[0]
    assert checked_plan == base_plan
    context = control_system.planner.run_for_state.call_args.args[0]
    assert context.state == SalesStates.STABLE
    assert context.plan.max_pay_for_order == 200
    persisted_plan = mock_change_plan_fact.set_new_plan_fact.call_args.args[0]
    assert persisted_plan == base_plan
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_adv_plan_fact_unchanged(complex_adv_mock, plan_data_mock, fact_data_mock):
    """Тест: план и факт не изменились с прошлого раза"""
    control_system = AdvControlSystem(max_last_period=2)

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
    ):
        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что check_equal_in_cache был вызван с любым plan и нашим fact
        mock_change_plan_fact.check_equal_in_cache.assert_called_once_with(
            ANY, fact_data_mock
        )
        mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_insufficient_data(complex_adv_mock, plan_data_mock, fact_data_mock):
    """Тест: недостаточно данных для определения состояния"""
    control_system = AdvControlSystem(max_last_period=2)

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=None,
        ),
    ):
        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что detect_campaign_state был вызван
        mock_change_plan_fact.check_equal_in_cache.assert_called_once()
        mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_optimal_state(complex_adv_mock, plan_data_mock):
    """Тест: состояние OPTIMAL, действий не требуется"""
    control_system = AdvControlSystem(max_last_period=2)

    # Создаем факт, который приведет к состоянию OPTIMAL
    fact_data_optimal = FactData(
        predict_orders=12.0,  # Больше плана (10)
        pay_for_order=80.0,  # Меньше target (100)
        original_orders=12,
        fact_method=FactMethods.DIRECT_SALES,
    )

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_optimal)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
    ):
        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что состояние было определено
        mock_change_plan_fact.check_equal_in_cache.assert_called_once()
        mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        SalesStates.OVERSPEND,
        SalesStates.UNDERPERFORM,
        SalesStates.STABLE
    ],
)
async def test_process_adv_successful_execution(
    complex_adv_mock, plan_data_mock, fact_data_mock, state
):
    """Тест: успешное выполнение для различных состояний"""
    control_system = AdvControlSystem(max_last_period=2)

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_planner = MagicMock()
    mock_planner.run_for_state = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=state,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        # Мокируем planner
        control_system.planner.run_for_state = AsyncMock()

        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что planner.run_for_state был вызван
        control_system.planner.run_for_state.assert_called_once()
        mock_session.commit.assert_called_once()

        # Проверяем, что set_new_plan_fact был вызван с любым plan и нашим fact
        mock_change_plan_fact.set_new_plan_fact.assert_called_once_with(
            ANY, fact_data_mock
        )


@pytest.mark.asyncio
async def test_process_adv_overspend_state(complex_adv_mock, plan_data_mock):
    """Тест: состояние OVERSPEND (перерасход)"""
    control_system = AdvControlSystem(max_last_period=2)

    # Создаем факт, который приведет к состоянию OVERSPEND
    fact_data_overspend = FactData(
        predict_orders=8.0,
        pay_for_order=300.0,  # Больше max (250)
        original_orders=8,
        fact_method=FactMethods.DIRECT_SALES,
    )

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_overspend)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        mock_session.commit = AsyncMock()
        control_system.planner.run_for_state = AsyncMock()

        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что состояние было OVERSPEND
        control_system.planner.run_for_state.assert_called_once()
        call_args = control_system.planner.run_for_state.call_args[0][0]
        assert call_args.state == SalesStates.OVERSPEND


@pytest.mark.asyncio
async def test_process_adv_with_different_max_last_period(complex_adv_mock, plan_data_mock, fact_data_mock):
    """Тест: проверка работы с разными значениями max_last_period"""
    control_system = AdvControlSystem(max_last_period=5)

    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ) as mock_updater_class,
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        control_system.planner.run_for_state = AsyncMock()
        mock_session.commit = AsyncMock()
        await control_system.process_adv(complex_adv_mock)

        # Проверяем, что AdvSettingAutoUpdater был создан с правильным max_last_period
        mock_updater_class.assert_called_once()
        call_args = mock_updater_class.call_args
        assert call_args[0][1] == 5  # max_last_period передан правильно


@pytest.mark.asyncio
async def test_process_adv_get_fact_data_raises_propagates(
    complex_adv_mock, plan_data_mock, fact_data_mock
):
    control_system = AdvControlSystem(max_last_period=2)
    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(side_effect=RuntimeError("fact boom"))

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
    ):
        with pytest.raises(RuntimeError, match="fact boom"):
            await control_system.process_adv(complex_adv_mock)
    mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_planner_raises_no_set_new_plan_fact(
    complex_adv_mock, plan_data_mock, fact_data_mock
):
    control_system = AdvControlSystem(max_last_period=2)
    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.OVERSPEND,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        control_system.planner.run_for_state = AsyncMock(
            side_effect=RuntimeError("planner boom")
        )
        with pytest.raises(RuntimeError, match="planner boom"):
            await control_system.process_adv(complex_adv_mock)

    mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_commit_raises_no_set_new_plan_fact(
    complex_adv_mock, plan_data_mock, fact_data_mock
):
    control_system = AdvControlSystem(max_last_period=2)
    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock(side_effect=OSError("commit failed"))

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.STABLE,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        control_system.planner.run_for_state = AsyncMock()
        with pytest.raises(OSError, match="commit failed"):
            await control_system.process_adv(complex_adv_mock)

    mock_change_plan_fact.set_new_plan_fact.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_set_new_plan_fact_raises_propagates(
    complex_adv_mock, plan_data_mock, fact_data_mock
):
    control_system = AdvControlSystem(max_last_period=2)
    mock_updater = MagicMock()
    mock_updater.get_fact_data = AsyncMock(return_value=fact_data_mock)

    mock_change_plan_fact = MagicMock()
    mock_change_plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    mock_change_plan_fact.set_new_plan_fact = AsyncMock(
        side_effect=RuntimeError("redis boom")
    )

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan_data_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.AdvSettingAutoUpdater",
            return_value=mock_updater,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.ChangePlanFact",
            return_value=mock_change_plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.detect_campaign_state",
            return_value=SalesStates.UNDERPERFORM,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.sm",
            return_value=mock_session,
        ),
    ):
        control_system.planner.run_for_state = AsyncMock()
        with pytest.raises(RuntimeError, match="redis boom"):
            await control_system.process_adv(complex_adv_mock)

    mock_session.commit.assert_called_once()


