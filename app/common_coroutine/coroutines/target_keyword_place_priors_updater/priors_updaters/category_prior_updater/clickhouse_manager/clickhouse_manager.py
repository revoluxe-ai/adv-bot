from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager


class ClickHouseManager(BaseClickHouseManager):
    async def update_category_prior(self):
        query = self._get_query("update_category_priors_updater")
        async with self._get_client() as client:
            await client.query(query)
