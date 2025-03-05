import time

from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.core.wb_api.mixins.statistic_mixin.wb_statistic_obj import CommonStat
from app.utils.click_house.client import get_clickhouse_client
from .wb_api import WBApi
from datetime import datetime
from typing import List


class WBCommonStatManager:

    def __init__(self, wb_access: WBCabinetAccess):
        self.wb_access = wb_access
        self.wb_api = WBApi(wb_access=wb_access)

    async def update_common_statistic(self, nmids: List[int]):
        # Получаем статистику для каждого nmid
        statistics: List[CommonStat] = await self.wb_api.get_cards_stats_by_days(nmids, 2)

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
                stat.buy_outs
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
        query += ",".join([f"({', '.join(map(str, value))}, {version})" for value in values])

        async with get_clickhouse_client() as client:
            await client.query(query)





