"""ClickHouse helpers for daily common-card statistics."""

import logging
import time
from datetime import datetime, timedelta

from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.statistic_mixin.wb_statistic_obj import CommonStat
from app.modules.shop_runner.modules.wb_api import WBApi
from app.settings import settings
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client
from .types.common_card_stat import CommonCardStat

logger = logging.getLogger(__name__)


async def get_stats_for_last_period(nmid: int, days: int) -> CommonCardStat | None:
    """
    Получает статистику за последний период в количестве дней.
    :param nmid: Идентификатор nmids для получения статистики.
    :param days: Количество дней для запроса.
    :return: Объект CommonCardStat с последними данными.
    """
    # Вычисляем дату начала периода (сегодня - количество дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Формируем запрос для получения данных с параметрами
    query = """
    SELECT  SUM(open_card), SUM(add_to_cart), SUM(orders), SUM(orders_sum), SUM(buy_outs)
            FROM wb_common_stat
            WHERE nmid = %(nmid)s
              AND date BETWEEN %(start_date)s AND %(end_date)s
              AND version = (
                SELECT MAX(version)
                FROM wb_common_stat
                WHERE nmid = %(nmid)s
                  AND date BETWEEN %(start_date)s AND %(end_date)s
  )

    """

    # Параметры для запроса
    params = {
        "nmid": nmid,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            # Получаем результат запроса с параметрами
            result = await client.query(query, parameters=params)

            if not result:
                return None
            result_row = result.first_row

    # Преобразуем результат в объект CommonCardStat
    return CommonCardStat(
        nmid=nmid,
        open_card=result_row[0],
        add_to_cart=result_row[1],
        orders=result_row[2],
        orders_sum=result_row[3],
        buy_outs=result_row[4],
    )


async def get_stats_by_days(nmid: int, last_days: int) -> list[CommonCardStat]:
    """
    Возвращает статистику по дням за последние last_days.

    Args:
        nmid: артикул товара
        last_days: за какое количество дней нужна стата

    Returns:
        list[CommonCardStat]: статистика по дням
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=last_days)

    query = """
    SELECT
        toDate(date) AS stat_date,
        argMax(open_card, version) AS open_card,
        argMax(add_to_cart, version) AS add_to_cart,
        argMax(orders, version) AS orders,
        argMax(orders_sum, version) AS orders_sum,
        argMax(buy_outs, version) AS buy_outs
    FROM wb_common_stat
    WHERE nmid = %(nmid)s
      AND toDate(date) BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
    GROUP BY stat_date
    ORDER BY stat_date DESC
    """

    params = {
        "nmid": nmid,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(query, parameters=params)

    stats: list[CommonCardStat] = []
    for row in result.result_rows:
        stat = CommonCardStat(
            nmid=nmid,
            open_card=row[1],
            add_to_cart=row[2],
            orders=row[3],
            orders_sum=row[4],
            buy_outs=row[5],
        )
        stat.date = row[0]
        stats.append(stat)

    return stats


async def get_stats_by_date_range(
    nmid: int, start_date: datetime, end_date: datetime
) -> list[CommonCardStat]:
    """
    Возвращает статистику по дням за заданный диапазон дат.

    Args:
        nmid: Артикул товара.
        start_date: Начало диапазона включительно.
        end_date: Конец диапазона включительно.

    Returns:
        list[CommonCardStat]: Статистика по дням в обратном хронологическом порядке.
    """
    query = """
    SELECT
        toDate(date) AS stat_date,
        argMax(open_card, version) AS open_card,
        argMax(add_to_cart, version) AS add_to_cart,
        argMax(orders, version) AS orders,
        argMax(orders_sum, version) AS orders_sum,
        argMax(buy_outs, version) AS buy_outs
    FROM wb_common_stat
    WHERE nmid = %(nmid)s
      AND toDate(date) BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
    GROUP BY stat_date
    ORDER BY stat_date DESC
    """

    params = {
        "nmid": nmid,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(query, parameters=params)

    stats: list[CommonCardStat] = []
    for row in result.result_rows:
        stat = CommonCardStat(
            nmid=nmid,
            open_card=row[1],
            add_to_cart=row[2],
            orders=row[3],
            orders_sum=row[4],
            buy_outs=row[5],
        )
        stat.date = row[0]
        stats.append(stat)

    return stats


async def get_today_funnel_clicks(
    nmids: list[int], *, at: datetime | None = None
) -> int:
    """Возвращает сумму карточных переходов (open_card) за сегодня по nmids."""
    if not nmids:
        return 0
    today = (at or datetime.now()).strftime("%Y-%m-%d")
    query = """
    SELECT COALESCE(SUM(latest_open_card), 0) AS funnel_clicks
    FROM (
        SELECT
            nmid,
            argMax(open_card, version) AS latest_open_card
        FROM wb_common_stat
        WHERE nmid IN %(nmids)s
          AND date = %(report_date)s
        GROUP BY nmid
    )
    """
    params = {
        "nmids": nmids,
        "report_date": today,
    }
    async with anti_ch_crash_semaphore:
        async with get_clickhouse_client() as client:
            result = await client.query(query, parameters=params)
    if not result.result_rows:
        return 0
    return int(result.result_rows[0][0])



class WBCommonStatManager:
    def __init__(self, wb_api: WBApi):
        self.wb_api = wb_api
        self.wb_access = wb_api.access

    async def update_common_statistic(self, nmids: list[int]):
        """Обновляет воронку карточки в CH за ``FULL_STAT_THRESHOLD_DATES`` дней."""
        try:
            statistics: list[CommonStat] = await self.wb_api.get_cards_stats_by_days(
                nmids, settings.FULL_STAT_THRESHOLD_DATES
            )
        except ApiForbiddenError as exc:
            logger.error("Нет доступов к статистике")
            raise exc
        except Exception as e:
            logger.error("Ошибка получения общей статистики", exc_info=True)
            raise e
        try:
            await self._add_common_statistic_to_clickhouse(statistics)
        except Exception as exc:
            logger.error("Ошибка обновления статистики", exc_info=True)
            raise exc

    @staticmethod
    async def _add_common_statistic_to_clickhouse(statistics: list[CommonStat]):
        # Подготовка данных для вставки в таблицу
        values = [
            (
                stat.nmid,
                f"'{stat.date.strftime('%Y-%m-%d')}'",  # Преобразуем дату в строковый формат и добавляем кавычки
                stat.open_card,
                stat.add_to_cart,
                stat.orders,
                stat.orders_sum,
                stat.buy_outs,
                stat.buyouts_sum_rub,
            )
            for stat in statistics
        ]

        version = time.time()

        # Формируем запрос на вставку данных
        query = """
        INSERT INTO wb_common_stat
        (nmid, date, open_card, add_to_cart, orders, orders_sum, buy_outs, buyouts_sum_rub, version)
        VALUES
        """

        # Добавляем значения для вставки
        query += ",".join(
            [f"({', '.join(map(str, value))}, {version})" for value in values]
        )
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                await client.query(query)
        return None
