from app.core.clickhouse_manager import BaseClickHouseManager
from app.utils.click_house.client import get_clickhouse_client as get_client


class ClickhouseManager(BaseClickHouseManager):
    async def fill_keyword_deltas(self, time_from_hours: int):
        query = self._get_query('fill_keyword_deltas')
        async with get_client() as client:
            await client.query(query, parameters={'time_from_hours': time_from_hours})
