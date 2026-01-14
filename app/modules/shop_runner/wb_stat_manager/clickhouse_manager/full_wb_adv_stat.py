import logging
import time
from collections.abc import Iterable
from datetime import datetime, date
from typing import TypedDict

from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    SmallFullAdvStat,
    SmallFullAdvStatPerDay,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client


# Определим тип для статистики по ключевым словам
class KeywordStat(TypedDict):
    keyword: str
    views: int
    clicks: int
    spend: float


logger = logging.getLogger(__name__)


def concatenate_stats(
    auto_adv_stats: list[SmallFullAdvStatPerDay],
    auction_adv_stats: list[SmallFullAdvStatPerDay],
) -> list[SmallFullAdvStatPerDay]:
    """
    Функция для объединения статистики по авто и аукционным объявлениям также по дням.

    Args:
        auto_adv_stat:
        auction_adv_stat:

    Returns:
          SmallFullAdvStatPerDay:

    """
    dates_from_auto = {stat.date for stat in auto_adv_stats}
    dates_from_auction = {stat.date for stat in auction_adv_stats}
    all_dates = dates_from_auto.union(dates_from_auction)
    data_to_auto = {stat.date: stat for stat in auto_adv_stats}
    data_to_auction = {stat.date: stat for stat in auction_adv_stats}

    concatenate_stats = []

    for date in all_dates:
        auto_stat = data_to_auto.get(date)
        auction_stat = data_to_auction.get(date)
        if auto_stat and auction_stat:
            # Объединяем статистику по дням
            auto_stat.views += auction_stat.views
            auto_stat.clicks += auction_stat.clicks
            auto_stat.spend += auction_stat.spend
            auto_stat.added_to_cart += auction_stat.added_to_cart
            auto_stat.orders += auction_stat.orders
            auto_stat.sum_price += auction_stat.sum_price
            concatenate_stats.append(auto_stat)
        elif not auto_stat and auction_stat:
            # Если нет авто статистики, то берем аукционную
            concatenate_stats.append(auction_stat)
        elif not auction_stat and auto_stat:
            # Если нет аукционной статистики, то берем авто статистику
            concatenate_stats.append(auto_stat)

    concatenate_stats.sort(key=lambda x: x.date, reverse=True)

    return concatenate_stats


async def get_daily_stats_by_last_days(
    adv_ids: list[int], start_date: datetime, end_date: datetime
) -> list[SmallFullAdvStatPerDay]:
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            # Используем argMax вместо ROW_NUMBER() OVER - значительно эффективнее по памяти
            query = """
        SELECT
            date,
            SUM(latest_views) AS views,
            SUM(latest_clicks) AS clicks,
            SUM(latest_spend) AS spend,
            SUM(latest_added_to_cart) AS added_to_cart,
            SUM(latest_orders) AS orders,
            SUM(latest_sum_price_orders) AS sum_price_orders
        FROM (
            SELECT
                adv_id,
                date,
                argMax(views, version) AS latest_views,
                argMax(clicks, version) AS latest_clicks,
                argMax(spend, version) AS latest_spend,
                argMax(added_to_cart, version) AS latest_added_to_cart,
                argMax(orders, version) AS latest_orders,
                argMax(sum_price_orders, version) AS latest_sum_price_orders
            FROM default_db.full_adv_wb_stat
            WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
            AND adv_id IN %(adv_ids)s
            GROUP BY adv_id, date
        )
        GROUP BY date
        ORDER BY date
        """
            try:
                res = await client.query(
                    query,
                    parameters={
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "adv_ids": adv_ids,
                    },
                )
                rows = res.result_rows
                if not rows:
                    return []

                stats_per_day = [
                    SmallFullAdvStatPerDay(
                        date=row[0],
                        views=row[1],
                        clicks=row[2],
                        spend=row[3],
                        added_to_cart=row[4],
                        orders=row[5],
                        sum_price=row[6],
                    )
                    for row in rows
                ]
                return stats_per_day

            except Exception:
                logger.error(
                    "Ошибка получения дневной статистики из ClickHouse", exc_info=True
                )
                raise


async def get_stats_by_last_days(
    adv_ids: list[int], start_date: datetime, end_date: datetime
) -> SmallFullAdvStat:
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            # Используем argMax вместо ROW_NUMBER() OVER - значительно эффективнее по памяти
            query = """
            SELECT
                SUM(latest_views) AS views,
                SUM(latest_clicks) AS clicks,
                SUM(latest_spend) AS spend,
                SUM(latest_added_to_cart) AS added_to_cart,
                SUM(latest_orders) AS orders,
                SUM(latest_sum_price_orders) AS sum_price_orders
            FROM (
                SELECT
                    adv_id,
                    date,
                    argMax(views, version) AS latest_views,
                    argMax(clicks, version) AS latest_clicks,
                    argMax(spend, version) AS latest_spend,
                    argMax(added_to_cart, version) AS latest_added_to_cart,
                    argMax(orders, version) AS latest_orders,
                    argMax(sum_price_orders, version) AS latest_sum_price_orders
                FROM default_db.full_adv_wb_stat
                WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
                AND adv_id IN %(adv_ids)s
                GROUP BY adv_id, date
            )
            """
            try:
                # Выполняем запрос
                res = await client.query(
                    query,
                    parameters={
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "adv_ids": adv_ids,
                    },
                )
                result = res.first_item

                # Обрабатываем результат, создавая общий объект FullAdvStat
                if result:
                    row = result
                    views = row["views"]
                    clicks = row["clicks"]
                    spend = row["spend"]
                    added_to_cart = row["added_to_cart"]
                    orders = row["orders"]
                    sum_price_orders = row["sum_price_orders"]

                    # Собираем общую статистику в объект FullAdvStat
                    return SmallFullAdvStat(
                        views=views,
                        clicks=clicks,
                        spend=spend,
                        added_to_cart=added_to_cart,
                        orders=orders,
                        sum_price=sum_price_orders,
                    )
                else:
                    # Если нет данных
                    return SmallFullAdvStat(
                        views=0,
                        clicks=0,
                        spend=0,
                        added_to_cart=0,
                        orders=0,
                        sum_price=0,
                    )
            except Exception:
                logger.error("Ошибка получения статистики из ClickHouse", exc_info=True)
                raise


def _get_insert_query() -> str:
    query = """
    INSERT INTO default_db.full_adv_wb_stat (adv_id,
     date,
      views,
       clicks,
        spend,
         added_to_cart,
          orders,
           sum_price_orders,
            version)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return query


async def insert(stats: Iterable[FullAdvStat]) -> None:
    if not stats:
        return
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            # Получаем запрос для вставки
            query = _get_insert_query()
            version = str(time.time())
            # Подготовим параметры для вставки
            values = []
            for stat in stats:
                adv_id = stat.advertId  # ID рекламного объявления
                for day in stat.days:
                    # Вставляем данные каждого дня как параметры
                    values.append(
                        [
                            adv_id,
                            day.date.strftime("%Y-%m-%d"),
                            day.views,
                            day.clicks,
                            day.sum,
                            day.atbs,
                            day.orders,
                            day.sum_price,
                            version,  # Здесь можно использовать значение для версии
                        ]
                    )

            for row in values:
                query_result = await client.query(query, parameters=row)
                logger.debug(query_result)


async def get_keywords_spend(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> float:
    """
    Возвращает общие затраты по ключевым словам за период [start_date, end_date]
    по агрегатам из `mv_clusters_daily_agg`.
    """

    if not adv_ids:
        return 0.0

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    adv_ids_str = ", ".join(map(str, adv_ids))

    query = f"""
        WITH aggregated AS (
            SELECT
                argMaxMerge(views_state) AS views,
                argMaxMerge(clicks_state) AS clicks,
                argMaxMerge(cpm_state) AS cpm
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND date BETWEEN toDate('{start_date_str}') AND toDate('{end_date_str}')
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            COALESCE(SUM(cpm * views) / 1000.0, 0.0) AS total_spend
        FROM aggregated
    """

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(query)
                result = res.first_item
                return float(result["total_spend"]) if result else 0.0
    except Exception:
        logger.error(
            "Ошибка получения суммы трат по ключам из ClickHouse", exc_info=True
        )
        return 0.0


# TODO: Внедрить отображение ключей из статистики API, попробовать вернуть управление ставкой по позициям


# TODO:  Добавить в бот указатель, который показывает, что по настройкам достигнут максимум и дальше поможет только перестроойка плана продаж


async def get_keywords_views_by_days(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> dict[date, int]:
    """
    Возвращает показы по ключевым словам по дням за период [start_date, end_date]
    из аггрегированных `mv_clusters_daily_agg`.

    Returns:
        dict[date, int]: {дата: суммарные показы по ключевым словам за этот день}
    """
    import datetime as dt

    if not adv_ids:
        return {}

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    adv_ids_str = ", ".join(map(str, adv_ids))

    query = f"""
        WITH aggregated AS (
            SELECT
                date,
                argMaxMerge(views_state) AS views
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND date BETWEEN toDate('{start_date_str}') AND toDate('{end_date_str}')
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            date,
            COALESCE(SUM(views), 0) AS total_views
        FROM aggregated
        GROUP BY date
        ORDER BY date
    """

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(query)
                rows = res.result_rows

                result: dict[dt.date, int] = {}
                current_date = dt.date.fromisoformat(start_date_str)
                end_date_obj = dt.date.fromisoformat(end_date_str)
                while current_date <= end_date_obj:
                    result[current_date] = 0
                    current_date += dt.timedelta(days=1)

                for row in rows:
                    if row and len(row) >= 2 and row[0] is not None:
                        date_val = row[0]
                        views = int(row[1]) if row[1] is not None else 0
                        result[date_val] = views
                return result

    except Exception:
        logger.error(
            "Ошибка получения показов по ключам по дням из ClickHouse",
            exc_info=True,
        )
        return {}


async def get_keywords_clicks_and_views(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> tuple[int, int]:
    """
    Возвращает общие клики и показы по ключевым словам за период [start_date, end_date]
    по агрегатам `mv_clusters_daily_agg`.
    """

    if not adv_ids:
        return 0, 0

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    adv_ids_str = ", ".join(map(str, adv_ids))

    query = f"""
        WITH aggregated AS (
            SELECT
                argMaxMerge(views_state) AS views,
                argMaxMerge(clicks_state) AS clicks
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND date BETWEEN toDate('{start_date_str}') AND toDate('{end_date_str}')
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(views), 0) AS total_views
        FROM aggregated
    """

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(query)
                result = res.first_item
                if result:
                    return int(result["total_clicks"]), int(result["total_views"])
                return 0, 0
    except Exception:
        logger.error(
            "Ошибка получения суммы кликов и показов по ключам из ClickHouse",
            exc_info=True,
        )
        return 0, 0
