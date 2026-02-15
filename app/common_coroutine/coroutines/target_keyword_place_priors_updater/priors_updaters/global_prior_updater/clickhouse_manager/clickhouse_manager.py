from app.core.clickhouse_manager.base_clickhouse_manager import  BaseClickHouseManager



class ClickHouseManager(BaseClickHouseManager):


    async def update_global_prior(self):
        query = self._get_query("update_global_priors")
        async with self._get_client() as client:
            await client.query(query)

