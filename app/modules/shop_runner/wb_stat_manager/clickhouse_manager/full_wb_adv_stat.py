import logging
import time
from collections.abc import Iterable
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    SmallFullAdvStat,
    SmallFullAdvStatPerDay,
)
from app.shared.domains.wb.utils.additional_cost_per_order import (
    compute_additional_cost_per_order,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore, run_ch_with_timeout
from app.utils.click_house.client import get_clickhouse_client


# Определим тип для статистики по ключевым словам
class KeywordStat(TypedDict):
    keyword: str
    views: int
    clicks: int
    spend: float


logger = logging.getLogger(__name__)


def _load_sql_query(query_name: str) -> str:
    sql_path = Path(__file__).parent / "sql" / f"{query_name}.sql"
    return sql_path.read_text(encoding="utf-8")


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

    concatenate_stats: list[SmallFullAdvStatPerDay] = []

    for day in all_dates:
        auto_stat = data_to_auto.get(day)
        auction_stat = data_to_auction.get(day)
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
                result = cast(dict[str, Any] | None, getattr(res, "first_item", None))

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


async def get_stats_by_adv_ids_last_days(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> dict[int, SmallFullAdvStat]:
    """Вернуть exact-leg статистику по каждому adv_id для spec leg-cpo-economics.

    В отличие от get_stats_by_last_days результат не суммирует разные рекламные
    ноги между собой: каждый concrete adv_id остаётся отдельной строкой.
    """
    if not adv_ids:
        return {}
    query = """
    SELECT
        adv_id,
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
    GROUP BY adv_id
    ORDER BY adv_id
    """
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(
                query,
                parameters={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "adv_ids": adv_ids,
                },
            )
    return {
        int(row[0]): SmallFullAdvStat(
            views=int(row[1] or 0),
            clicks=int(row[2] or 0),
            spend=float(row[3] or 0.0),
            added_to_cart=int(row[4] or 0),
            orders=int(row[5] or 0),
            sum_price=float(row[6] or 0.0),
        )
        for row in result.result_rows
    }


async def get_spend_by_last_days(
    adv_ids: list[int], start_date: datetime, end_date: datetime
) -> float:
    if not adv_ids:
        return 0.0

    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")
    query = _load_sql_query("get_spend_by_last_days")

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(
                    query,
                    parameters={
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "adv_ids": adv_ids,
                    },
                )
                result = cast(dict[str, Any] | None, getattr(res, "first_item", None))
                total_spend = result["total_spend"] if result else 0.0
                return float(total_spend or 0.0)
    except Exception:
        logger.error("Ошибка получения затрат из ClickHouse", exc_info=True)
        raise


async def get_total_spend_by_advs(adv_ids: list[int]) -> float:
    """Суммарный расход кампаний за всю историю (абсолютный/lifetime spend).

    В отличие от ``get_spend_by_last_days`` период не ограничивается: берутся
    все дни, что есть в ``default_db.full_adv_wb_stat``. Используется гейтом
    абсолютного лимита бюджета РК.

    Args:
        adv_ids: ID кампаний (Авто и/или Аукцион); пустой список — 0.0.

    Returns:
        Суммарный расход в рублях.

    Raises:
        Exception: пробрасывает ошибки ClickHouse после логирования; вызывающий
            код решает, трактовать это как fail-open или нет.
    """
    if not adv_ids:
        return 0.0

    query = _load_sql_query("get_total_spend_by_advs")

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(
                    query,
                    parameters={"adv_ids": adv_ids},
                )
                result = cast(dict[str, Any] | None, getattr(res, "first_item", None))
                total_spend = result["total_spend"] if result else 0.0
                return float(total_spend or 0.0)
    except Exception:
        logger.error(
            "Ошибка получения суммарных затрат за всю историю из ClickHouse",
            exc_info=True,
        )
        raise


async def get_additional_cost_per_order_for_adv(
    adv_id: int, days: int = 7
) -> float | None:
    """Средняя себестоимость заказа из дополнительных показов (полки/рек. системы) за период.

    Args:
        adv_id: ID авто-кампании
        days: Количество дней (по умолчанию 7)

    Returns:
        Себестоимость заказа из доп. показов или None при ошибке
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    auto_stat = await get_stats_by_last_days(
        [adv_id], start_date, end_date
    )
    spend_kw = await get_keywords_spend(
        [adv_id], start_date, end_date
    )
    kw_views_orders = await get_keywords_views_orders_by_days(
        [adv_id], start_date, end_date
    )

    orders_kw = sum(orders for _, orders in kw_views_orders.values())
    return compute_additional_cost_per_order(
        auto_stat.spend,
        auto_stat.orders,
        spend_kw,
        orders_kw,
    )


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

    async def _insert_stats() -> None:
        async with get_clickhouse_client() as client:
            query = _get_insert_query()
            version = str(time.time())
            values: list[list[int | float | str]] = []
            for stat in stats:
                adv_id = stat.advertId
                for day in stat.days:
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
                            version,
                        ]
                    )

            for row in values:
                query_result = await client.query(query, parameters=cast(Any, row))
                logger.debug(query_result)

    await run_ch_with_timeout(_insert_stats())


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
                result = cast(dict[str, Any] | None, getattr(res, "first_item", None))
                return float(result["total_spend"]) if result else 0.0
    except Exception:
        logger.error(
            "Ошибка получения суммы трат по ключам из ClickHouse", exc_info=True
        )
        return 0.0


# TODO: Внедрить отображение ключей из статистики API, попробовать вернуть управление ставкой по позициям


# TODO:  Добавить в бот указатель, который показывает, что по настройкам достигнут максимум и дальше поможет только перестроойка плана продаж


_KeywordDailyMetric = Literal["views", "clicks"]


def _keyword_daily_metric_sql_parts(metric: _KeywordDailyMetric) -> tuple[str, str, str]:
    """Return (merge_state_column, inner_alias, total_alias) for mv_clusters_daily_agg."""
    if metric == "views":
        return "views_state", "views", "total_views"
    return "clicks_state", "clicks", "total_clicks"


async def _get_keywords_metric_by_days(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
    *,
    metric: _KeywordDailyMetric,
    error_log_message: str,
) -> dict[date, int]:
    """Shared: daily sum of views or clicks from `mv_clusters_daily_agg` by keyword clusters."""
    if not adv_ids:
        return {}

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    adv_ids_str = ", ".join(map(str, adv_ids))
    merge_state, inner_alias, total_alias = _keyword_daily_metric_sql_parts(metric)

    query = f"""
        WITH aggregated AS (
            SELECT
                date,
                argMaxMerge({merge_state}) AS {inner_alias}
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND date BETWEEN toDate('{start_date_str}') AND toDate('{end_date_str}')
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            date,
            COALESCE(SUM({inner_alias}), 0) AS {total_alias}
        FROM aggregated
        GROUP BY date
        ORDER BY date
    """
    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(query)
                rows = res.result_rows
                result: dict[date, int] = {}
                current = date.fromisoformat(start_date_str)
                end_d = date.fromisoformat(end_date_str)
                while current <= end_d:
                    result[current] = 0
                    current += timedelta(days=1)

                for row in rows:
                    if row and len(row) >= 2 and row[0] is not None:
                        day = row[0]
                        val = int(row[1]) if row[1] is not None else 0
                        result[day] = val
                return result
    except Exception:
        logger.error(error_log_message, exc_info=True)
        return {}


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
    return await _get_keywords_metric_by_days(
        adv_ids,
        start_date,
        end_date,
        metric="views",
        error_log_message="Ошибка получения показов по ключам по дням из ClickHouse",
    )


async def get_keywords_clicks_by_days(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> dict[date, int]:
    """Возвращает клики по ключевым словам по дням за период."""
    return await _get_keywords_metric_by_days(
        adv_ids,
        start_date,
        end_date,
        metric="clicks",
        error_log_message="Ошибка получения кликов по ключам по дням",
    )


async def get_keywords_views_orders_by_days(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
) -> dict[date, tuple[int, int]]:
    """
    Возвращает показы и заказы по ключевым словам по дням за период [start_date, end_date]
    из агрегированных `mv_clusters_daily_agg`.

    Returns:
        dict[date, tuple[int, int]]: {дата: (views, orders)}
    """

    # TODO: Норм ли считать конверсию в полках по заказам за неделю или надо за 2 недели или через корзины?
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
                argMaxMerge(views_state) AS views,
                argMaxMerge(orders_state) AS orders
            FROM default_db.mv_clusters_daily_agg
            WHERE
                adv_id IN ({adv_ids_str})
                AND date BETWEEN toDate('{start_date_str}') AND toDate('{end_date_str}')
            GROUP BY adv_id, nmid, norm_query, date
        )
        SELECT
            date,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(orders), 0) AS total_orders
        FROM aggregated
        GROUP BY date
        ORDER BY date DESC
    """

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                res = await client.query(query)
                rows = res.result_rows

                result: dict[dt.date, tuple[int, int]] = {}
                for row in rows:
                    if row and len(row) >= 3 and row[0] is not None:
                        date_val = row[0]
                        views = int(row[1]) if row[1] is not None else 0
                        orders = int(row[2]) if row[2] is not None else 0
                        result[date_val] = (views, orders)
                return result

    except Exception:
        logger.error(
            "Ошибка получения показов и заказов по ключам по дням из ClickHouse",
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
                result = cast(dict[str, Any] | None, getattr(res, "first_item", None))
                if result:
                    return int(result["total_clicks"]), int(result["total_views"])
                return 0, 0
    except Exception:
        logger.error(
            "Ошибка получения суммы кликов и показов по ключам из ClickHouse",
            exc_info=True,
        )
        return 0, 0


async def get_auto_total_clicks_today(
    adv_id: int, *, at: datetime | None = None
) -> int:
    """Возвращает суммарные клики авто-РК за сегодня."""
    end_date = at or datetime.now()
    start_date = end_date
    stats = await get_stats_by_last_days([adv_id], start_date, end_date)
    return int(stats.clicks or 0)
