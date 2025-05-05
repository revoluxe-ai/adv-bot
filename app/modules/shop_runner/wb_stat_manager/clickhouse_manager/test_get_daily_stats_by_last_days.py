import datetime

import pytest

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    get_daily_stats_by_last_days,
)


@pytest.mark.asyncio
async def test_concatenate_stats():
    test_auto_adv_id = 25040169
    test_auction_adv_id = 25040170

    pass_days = 3

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=pass_days)

    result_auto: list[SmallFullAdvStatPerDay] = await get_daily_stats_by_last_days(
        [test_auto_adv_id], start_date, end_date
    )

    result_auction: list[SmallFullAdvStatPerDay] = await get_daily_stats_by_last_days(
        [test_auction_adv_id], start_date, end_date
    )

    concat_result: list[SmallFullAdvStatPerDay] = full_wb_adv_stat.concatenate_stats(
        result_auto, result_auction
    )

    assert isinstance(concat_result, list)
    today = datetime.datetime.now().date()
    last_date = today - datetime.timedelta(days=pass_days)

    assert concat_result[-1].date == last_date
    assert len(concat_result) >= len(result_auto)
    assert len(concat_result) >= len(result_auction)


@pytest.mark.asyncio
async def test_get_daily_stats_by_last_days():
    test_adv_id = 25040169

    pass_days = 10

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=pass_days)

    result: list[SmallFullAdvStatPerDay] = await get_daily_stats_by_last_days(
        [test_adv_id], start_date, end_date
    )
    assert isinstance(result, list)
