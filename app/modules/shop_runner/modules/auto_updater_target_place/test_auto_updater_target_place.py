import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from sqlalchemy import Result

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.shop_runner.modules.auto_updater_target_place.auto_updater_target_place import (
    AutoUpdaterTargetPlace,
)
from .auto_updater_target_place import LastTargetPlaceUpdateRedisManager

now = datetime.datetime.now()


@pytest.fixture
def result_mock():
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
    adv_setting_mock.max_price_for_order = max_price_for_order
    adv_setting_mock.target_price_for_order = target_price_for_order
    adv_setting_mock.plan_for_sales_for_day = plan_for_sales_for_day
    adv_setting_mock.max_place = current_target_place

    redis_manager_mock = LastTargetPlaceUpdateRedisManager
    redis_manager_mock.get_last_target_place_update = AsyncMock(return_value=result)
    redis_manager_mock.set_last_target_place_update = AsyncMock()
    with (
        patch(
            "app.modules.shop_runner.modules.auto_updater_target_place."
            "auto_updater_target_place.LastTargetPlaceUpdateRedisManager",
            new=redis_manager_mock,
        ),
        patch(
            "app.modules.shop_runner.modules.auto_updater_target_place."
            "auto_updater_target_place.sm",
            new=get_async_session_mock,
        ),
    ):
        updater = AutoUpdaterTargetPlace()

        await updater.update_target_place(
            adv_setting_mock,
            fact_mean_price_for_order_for_last_two_days,
            fact_mean_orders_for_last_two_days,
            keywords_mocks,
        )
        if current_target_place != new_target_place:
            called_stmt = session_mock.execute.call_args[0][0]
            assert called_stmt.table.name == "advsetting"
            compiled = called_stmt.compile()
            assert compiled.params["max_place"] == new_target_place
            session_mock.commit.assert_awaited_once()
            redis_manager_mock.set_last_target_place_update.assert_awaited_once()
        else:
            session_mock.commit.assert_not_awaited()
