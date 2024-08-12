import asyncio
import clickhouse_connect

from app.settings import settings

host = settings.clickhouse_host
username = settings.clickhouse_user
password = settings.clickhouse_password


async def get_clickhouse_client():
    return await clickhouse_connect.create_async_client(
        host=host,
        username=username,
        password=password,
        database='default_db'
    )


