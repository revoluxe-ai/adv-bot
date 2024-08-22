import asyncio
import clickhouse_connect
from app.settings import settings

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password

# ch_max_thread = settings.CH_MAX_THREAD

class ClickHousePool:
    def __init__(self, max_size: int):
        self._max_size = max_size
        self._queue = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)

    async def _create_client(self):
        return await clickhouse_connect.create_async_client(
            host=host,
            username=username,
            password=password,
            database='default_db'
        )

    async def initialize_pool(self):
        for _ in range(self._max_size):
            client = await self._create_client()
            await self._queue.put(client)

    async def get_client(self):
        async with self._semaphore:
            return await self._queue.get()

    async def release_client(self, client):
        await self._queue.put(client)

pool = ClickHousePool(max_size=3000)

async def setup_pool():
    await pool.initialize_pool()

async def get_clickhouse_client():
    client = await pool.get_client()
    return client