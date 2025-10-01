import pytest

"""Tests for AutoUpdaterTargetPlace target place updating logic."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Result

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.auto_updater_target_place import (
    AutoUpdaterTargetPlace,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)

from .auto_updater_target_place import LastTargetPlaceUpdateRedisManager

now = datetime.datetime.now()


@pytest.fixture
def result_mock():
    """Return a mock Result object for tests."""
    result_mock = MagicMock(spec=Result)
    return result_mock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fact_mean_price_for_order_for_last_two_days,"
    "fact_mean_orders_for_last_two_days,"
    "result,"  # последняя сумма spend по ключам, последняя дата изменения целевой позиции
    "target_price_for_order,"
    "max_price_for_order,"
    "plan_for_sales_for_day,"
    "current_target_place,"
    "new_target_place",
    [
        (
            200,  # факт цена заказа
            1,  # факт количество заказов
            (
                now - datetime.timedelta(hours=5),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            5,  # начальная целевая позиция
            6,  # новая целевая позиция
        ),
        (
            50,  # факт цена заказа
            1,  # факт количество заказов
            (
                now - datetime.timedelta(hours=5),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            2,  # начальная целевая позиция
            1,  # новая целевая позиция
        ),
        (
            50,  # факт цена заказа
            1,  # факт количество заказов
            (
                now - datetime.timedelta(hours=5),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            1,  # начальная целевая позиция
            1,  # новая целевая позиция
        ),
        (
            50,  # факт цена заказа
            15,  # факт количество заказов
            (
                now - datetime.timedelta(hours=5),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            5,  # начальная целевая позиция
            5,  # новая целевая позиция
        ),
        (
            10,  # факт цена заказа
            15,  # факт количество заказов
            (
                now - datetime.timedelta(hours=5),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            5,  # начальная целевая позиция
            5,  # новая целевая позиция
        ),
        (
            60,  # факт цена заказа
            15,  # факт количество заказов
            (
                now - datetime.timedelta(minutes=20),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            5,  # начальная целевая позиция
            5,  # новая целевая позиция
        ),
        (
            60,  # факт цена заказа
            15,  # факт количество заказов
            (
                now - datetime.timedelta(minutes=70),  # прошлое последнее обновление
                10,  # сумма spend по ключам из редис
            ),
            50,  # целевая цена заказа
            150,  # максимальная цена заказа
            10,  # план продаж в день
            5,  # начальная целевая позиция
            6,  # новая целевая позиция
        ),
    ],
)
async def test_update_target_place(
    fact_mean_price_for_order_for_last_two_days: float,
    fact_mean_orders_for_last_two_days: int,
    result: tuple[datetime.datetime, float] | None,
    target_price_for_order: float,
    max_price_for_order: float,
    plan_for_sales_for_day: int,
    current_target_place: int,
    new_target_place: int,
    adv_setting_mock: MagicMock,
    keywords_mocks: list[CalculatedKeyword],
    get_async_session_mock,
    session_mock,
) -> None:
    """Verify target place update logic across scenarios."""
    adv_setting_mock.max_price_for_order = max_price_for_order
    adv_setting_mock.target_price_for_order = target_price_for_order
    adv_setting_mock.plan_for_sales_for_day = plan_for_sales_for_day
    adv_setting_mock.max_place = current_target_place

    # Prepare a redis manager instance with async methods and a factory that
    # returns it when called from production code (LastTargetPlaceUpdateRedisManager(adv))
    redis_manager_instance = MagicMock()
    redis_manager_instance.get_last_target_place_update = AsyncMock(return_value=result)
    redis_manager_instance.set_last_target_place_update = AsyncMock()
    # Factory used to replace the class in the module; calling it returns the instance
    redis_manager_factory = lambda adv: redis_manager_instance

    plan_data = PlanData(
        orders=plan_for_sales_for_day,
        target_pay_for_order=target_price_for_order,
        max_pay_for_order=max_price_for_order,
    )

    fact_data = FactData(
        predict_orders=fact_mean_orders_for_last_two_days,
        pay_for_order=fact_mean_price_for_order_for_last_two_days,
        original_orders=fact_mean_orders_for_last_two_days,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place."
            "auto_updater_target_place.LastTargetPlaceUpdateRedisManager",
            new=redis_manager_factory,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place."
            "auto_updater_target_place.sm",
            new=get_async_session_mock,
        ),
    ):
        # Подготовим необходимые глобальные переменные и заменим класс RedisManager
        # на фабрику, возвращающую заранее подготовленный экземпляр.
        import importlib

        module = importlib.import_module(
            "app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.auto_updater_target_place"
        )
        # adv используется в функции как глобальная переменная (legacy bug)
        setattr(module, "adv", adv_setting_mock)
        # spend_sum_from_keywords_now — сумма spend по ключам
        setattr(
            module,
            "spend_sum_from_keywords_now",
            sum(getattr(k, "spend", 0) for k in keywords_mocks),
        )
        # legacy names for fact values
        setattr(
            module,
            "fact_mean_price_for_order_for_last_two_days",
            fact_data.pay_for_order,
        )
        setattr(
            module,
            "fact_mean_orders_for_last_two_days",
            fact_data.predict_orders,
        )
        # Replace LastTargetPlaceUpdateRedisManager class with factory returning our instance
        setattr(
            module,
            "LastTargetPlaceUpdateRedisManager",
            lambda adv: redis_manager_instance,
        )

        updater = AutoUpdaterTargetPlace(adv_setting_mock)

        await updater.update(
            keywords_mocks,
            plan_data,
            fact_data,
        )
        if current_target_place != new_target_place:
            called_stmt = session_mock.execute.call_args[0][0]
            assert called_stmt.table.name == "advsetting"
            compiled = called_stmt.compile()
            assert compiled.params["max_place"] == new_target_place
            session_mock.commit.assert_awaited_once()
            redis_manager_instance.set_last_target_place_update.assert_awaited_once()
        else:
            session_mock.commit.assert_not_awaited()
        # Cleanup pending tasks to prevent interference with other tests
        import asyncio

        current = asyncio.current_task()
        for task in list(asyncio.all_tasks()):
            if task is current:
                continue
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except Exception:
                pass
