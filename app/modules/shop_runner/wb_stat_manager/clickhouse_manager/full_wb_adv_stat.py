import time
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, TypedDict
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat, SmallFullAdvStatPerDay
from app.utils.click_house.client import get_clickhouse_client
import logging


# Определим тип для статистики по ключевым словам
class KeywordStat(TypedDict):
    keyword: str
    views: int
    clicks: int
    spend: float


logger = logging.getLogger(__name__)


async def get_daily_stats_by_last_days(adv_ids: list[int],
                                       start_date: datetime,
                                       end_date: datetime) -> list[SmallFullAdvStatPerDay]:

    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    async with get_clickhouse_client() as client:
        query = """
        WITH max_versions AS (
            SELECT *, 
                   ROW_NUMBER() OVER (PARTITION BY adv_id, date ORDER BY version DESC) AS row_num
            FROM default_db.full_adv_wb_stat
            WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
            AND adv_id IN %(adv_ids)s
        )
        SELECT 
            date,
            SUM(views) AS views, 
            SUM(clicks) AS clicks, 
            SUM(spend) AS spend, 
            SUM(added_to_cart) AS added_to_cart, 
            SUM(orders) AS orders, 
            SUM(sum_price_orders) AS sum_price_orders
        FROM max_versions
        WHERE row_num = 1
        GROUP BY date
        ORDER BY date
        """

        try:
            res = await client.query(query, parameters={
                "start_date": start_date_str,
                "end_date": end_date_str,
                "adv_ids": adv_ids
            })
            rows = res.result_rows
            if not rows:
                return []

            stats_per_day = [
                SmallFullAdvStatPerDay(
                    date=row["date"],
                    views=row["views"],
                    clicks=row["clicks"],
                    spend=row["spend"],
                    added_to_cart=row["added_to_cart"],
                    orders=row["orders"],
                    sum_price=row["sum_price_orders"]
                )
                for row in rows
            ]
            return stats_per_day

        except Exception:
            logger.error("Ошибка получения дневной статистики из ClickHouse", exc_info=True)
            raise


async def get_stats_by_last_days(adv_ids: list[int], start_date: datetime, end_date: datetime) -> SmallFullAdvStat:
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    async with get_clickhouse_client() as client:
        query = """
        WITH max_versions AS (
            SELECT *, 
                   ROW_NUMBER() OVER (PARTITION BY adv_id, date ORDER BY version DESC) AS row_num
            FROM default_db.full_adv_wb_stat
            WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s) 
            AND adv_id IN %(adv_ids)s
        )
        SELECT 
            SUM(views) AS views, 
            SUM(clicks) AS clicks, 
            SUM(spend) AS spend, 
            SUM(added_to_cart) AS added_to_cart, 
            SUM(orders) AS orders, 
            SUM(sum_price_orders) AS sum_price_orders
        FROM max_versions
        WHERE row_num = 1

"""
        try:
            # Выполняем запрос
            res = await client.query(query, parameters={
                "start_date": start_date_str,
                "end_date": end_date_str,
                "adv_ids": adv_ids
            })
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
                    sum_price=sum_price_orders
                )
            else:
                # Если нет данных
                return SmallFullAdvStat(
                    views=0,
                    clicks=0,
                    spend=0,
                    added_to_cart=0,
                    orders=0,
                    sum_price=0)
        except Exception:
            logger.error('Ошибка получения статистики из ClickHouse', exc_info=True)
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


async def insert(stats: Iterable[FullAdvStat]):
    if not stats:
        return

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
                values.append([
                    adv_id,
                    day.date.strftime('%Y-%m-%d'),
                    day.views,
                    day.clicks,
                    day.sum,
                    day.atbs,
                    day.orders,
                    day.sum_price,
                    version  # Здесь можно использовать значение для версии
                ])

        try:
            for row in values:
                await client.query(query, parameters=row)
        except Exception:
            logger.error('Ошибка вставки в кликхаус', exc_info=True)


async def get_keywords_spend(adv_ids: list[int],
                             start_date: datetime,
                             end_date: datetime,
                             table_name: str) -> float:
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    async with get_clickhouse_client() as client:
        query = f"""
        WITH max_versions AS (
            SELECT *, 
                   ROW_NUMBER() OVER (PARTITION BY adv_id, date, text ORDER BY version DESC) AS row_num
            FROM default_db.{table_name}
            WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
            AND adv_id IN %(adv_ids)s
        )
        SELECT SUM(spend) AS total_spend
        FROM max_versions
        WHERE row_num = 1
        """
        try:
            res = await client.query(query, parameters={
                "start_date": start_date_str,
                "end_date": end_date_str,
                "adv_ids": adv_ids
            })
            result = res.first_item

            return result["total_spend"] if result and result["total_spend"] is not None else 0.0

        except Exception:
            logger.error('Ошибка получения суммы трат по ключам из ClickHouse', exc_info=True)
            return 0.0


async def get_keyword_stats_by_last_days(adv_ids: list[int], start_date: datetime, end_date: datetime) -> List[
    KeywordStat]:
    """
    Получает статистику по ключевым словам за указанный период.
    
    Args:
        adv_ids: Список ID рекламных кампаний
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        
    Returns:
        Список объектов KeywordStat с данными по каждому ключевому слову
    """
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    async with get_clickhouse_client() as client:
        query = """
        WITH max_versions AS (
            SELECT *, 
                   ROW_NUMBER() OVER (PARTITION BY adv_id, date, text ORDER BY version DESC) AS row_num
            FROM default_db.advkeyword
            WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
            AND adv_id IN %(adv_ids)s
        )
        SELECT 
            text as keyword,
            SUM(views) AS views, 
            SUM(clicks) AS clicks, 
            SUM(spend) AS spend
        FROM max_versions
        WHERE row_num = 1
        GROUP BY keyword
        """
        try:
            res = await client.query(query, parameters={
                "start_date": start_date_str,
                "end_date": end_date_str,
                "adv_ids": adv_ids
            })

            results = []
            for row in res:
                keyword_stat = KeywordStat(
                    keyword=row["keyword"],
                    views=row["views"],
                    clicks=row["clicks"],
                    spend=row["spend"]
                )
                results.append(keyword_stat)

            return results

        except Exception:
            logger.error('Ошибка получения статистики по ключевым словам из ClickHouse', exc_info=True)
            return []
