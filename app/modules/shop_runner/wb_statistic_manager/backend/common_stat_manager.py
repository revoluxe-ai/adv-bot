import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.statistic_mixin.wb_statistic_obj import CommonStat
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.utils.click_house.client import get_clickhouse_client
from .types.common_card_stat import CommonCardStat
from .wb_api import WBApi

logger = logging.getLogger(__name__)


async def get_stats_for_last_period(nmid: int, days: int) -> Optional[CommonCardStat]:
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
        SUM(open_card) AS open_card,
        SUM(add_to_cart) AS add_to_cart,
        SUM(orders) AS orders,
        SUM(orders_sum) AS orders_sum,
        SUM(buy_outs) AS buy_outs
    FROM wb_common_stat
    WHERE nmid = %(nmid)s
      AND date BETWEEN %(start_date)s AND %(end_date)s
      AND version = (
        SELECT MAX(version)
        FROM wb_common_stat AS inner_stat
        WHERE inner_stat.nmid = %(nmid)s
          AND inner_stat.date = wb_common_stat.date
      )
    GROUP BY stat_date
    ORDER BY stat_date DESC
    """

    params = {
        "nmid": nmid,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }

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


class WBCommonStatManager:

    def __init__(self, wb_access: WBCabinetAccess):
        self.wb_access = wb_access
        self.wb_api = WBApi(wb_access=wb_access)

    async def update_common_statistic(self, nmids: List[int]):
        try:
            statistics: List[CommonStat] = await self.wb_api.get_cards_stats_by_days(
                nmids, 6
            )
        except ApiForbiddenError as exc:
            logger.error("Нет доступов к статистике")
            raise exc
        except Exception as e:
            logger.error("Ошибка получения общей статистики", exc_info=True)
            raise e
        # Добавляем статистику в ClickHouse
        await self._add_common_statistic_to_clickhouse(statistics)

    async def _add_common_statistic_to_clickhouse(self, statistics: List[CommonStat]):
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
            )
            for stat in statistics
        ]

        version = time.time()

        # Формируем запрос на вставку данных
        query = """
        INSERT INTO wb_common_stat
        (nmid, date, open_card, add_to_cart, orders, orders_sum, buy_outs, version)
        VALUES
        """

        # Добавляем значения для вставки
        query += ",".join(
            [f"({', '.join(map(str, value))}, {version})" for value in values]
        )

        async with get_clickhouse_client() as client:
            await client.query(query)
