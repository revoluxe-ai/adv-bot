"""Сервис расчёта конверсии рекомендательного трафика (показы→заказы)."""

import datetime
import logging

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

logger = logging.getLogger(__name__)

REC_VIEWS_TARGET = 1000
LOOKBACK_DAYS = 30


async def get_rec_conversion(
    auto_adv_id: int,
    start_date: datetime.datetime | None = None,
    end_date: datetime.datetime | None = None,
) -> float:
    """
    Конверсия рекомендательного трафика: orders / views по последним REC_VIEWS_TARGET
    показам рекомендаций (авто‑РК минус трафик по ключам), округляя до полных дней.

    Returns:
        rec_conversion: sum(rec_orders) / sum(rec_views), или 0.0 если rec_views == 0
    """
    if end_date is None:
        end_date = datetime.datetime.now()
    if start_date is None:
        start_date = end_date - datetime.timedelta(days=LOOKBACK_DAYS)

    auto_stats = await full_wb_adv_stat.get_daily_stats_by_last_days(
        [auto_adv_id], start_date, end_date
    )
    kw_stats = await full_wb_adv_stat.get_keywords_views_orders_by_days(
        [auto_adv_id], start_date, end_date
    )

    auto_by_date: dict[datetime.date, SmallFullAdvStatPerDay] = {
        s.date: s for s in auto_stats
    }

    rec_views_by_date: list[tuple[datetime.date, int, int]] = []
    for d, stat in sorted(auto_by_date.items(), reverse=True):
        kw_v, kw_o = kw_stats.get(d, (0, 0))
        rec_v = max(0, stat.views - kw_v)
        rec_o = max(0, stat.orders - kw_o)
        if rec_v > 0 or rec_o > 0:
            rec_views_by_date.append((d, rec_v, rec_o))

    total_rec_views = 0
    total_rec_orders = 0
    for d, rec_v, rec_o in rec_views_by_date:
        total_rec_views += rec_v
        total_rec_orders += rec_o
        if total_rec_views >= REC_VIEWS_TARGET:
            break

    if total_rec_views == 0:
        return 0.0
    return total_rec_orders / total_rec_views
