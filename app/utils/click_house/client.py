import asyncio
import clickhouse_connect
from app.settings import settings

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password
database = 'default_db'
max_connections = settings.CH_MAX_THREAD

semaphore = asyncio.Semaphore(max_connections)

class get_clickhouse_client:
    def __init__(self):
        self.client = None

    async def __aenter__(self):
        async with semaphore:
            self.client = await clickhouse_connect.create_async_client(
                host=host,
                username=username,
                password=password,
                database=database
            )
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()