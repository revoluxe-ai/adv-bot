import asyncio
import clickhouse_connect
from app.settings import settings

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password
import logging

logger = logging.getLogger(__name__)



class ClickHousePool:
    def __init__(self, max_size: int):
        self._max_size = max_size
        self._queue = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)
        self._open_connections = 0  # Счетчик открытых соединений
        self._lock = asyncio.Lock()  # Для синхронизации доступа к счетчику

    async def _create_client(self):
        async with self._lock:
            self._open_connections += 1  # Увеличение счетчика при создании клиента
        logger.debug(f"Client created. Total open connections: {self._open_connections}")
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

    async def close_all_clients(self):
        async with self._lock:
            while not self._queue.empty():
                client = await self._queue.get()
                await client.close()  # Закрытие соединения
                self._open_connections -= 1  # Уменьшение счетчика после закрытия соединения

    def get_open_connections_count(self):
        return self._open_connections  # Возвращаем текущее количество открытых соединений

pool = ClickHousePool(max_size=3000)

async def setup_pool():
    await pool.initialize_pool()

async def get_clickhouse_client():
    client = await pool.get_client()
    return client
