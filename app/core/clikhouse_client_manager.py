from contextlib import asynccontextmanager
from app.utils.click_house.client import get_clickhouse_client


@asynccontextmanager
async def get_client():
    """Асинхронный контекстный менеджер для получения клиента ClickHouse."""
    async with get_clickhouse_client() as clickhouse_client:
        yield clickhouse_client
