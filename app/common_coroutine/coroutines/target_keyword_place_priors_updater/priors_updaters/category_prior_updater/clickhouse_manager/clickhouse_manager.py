from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.utils.click_house.client import get_clickhouse_client as get_client

class ClickHouseManager(BaseClickHouseManager):
    async def update_category_prior(self):
        query = self._get_query("update_category_priors_updater")
        async with get_client() as client:
            await client.query(query)
