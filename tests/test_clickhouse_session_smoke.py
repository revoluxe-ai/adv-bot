import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.utils.ch_semaphore import anti_ch_crash_semaphore

pytestmark = pytest.mark.integration

# Пример теста для проверки тестовой сессии ClickHouse


@pytest.mark.asyncio
async def test_clickhouse_session_smoke(clickhouse_client: AsyncClient):
    """Проверяем, что async-клиент ClickHouse реально работает и БД отвечает"""
    async with anti_ch_crash_semaphore:
        result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1


@pytest.mark.asyncio
async def test_clickhouse_create_table(clickhouse_client: AsyncClient):
    """Пример: создание таблицы в тестовой ClickHouse"""
    # Создаём тестовую таблицу
    await clickhouse_client.command(
        """
        CREATE TABLE IF NOT EXISTS test_table (
            id UInt32,
            name String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id
        """
    )

    # Вставляем тестовые данные
    await clickhouse_client.insert(
        "test_table",
        [[1, "test_name"], [2, "another_name"]],
        column_names=["id", "name"]
    )
    async with anti_ch_crash_semaphore:
        # Проверяем, что данные были вставлены
        result = await clickhouse_client.query("SELECT COUNT(*) FROM test_table")
    assert result.result_rows[0][0] == 2

    # Очищаем таблицу после теста
    await clickhouse_client.command("DROP TABLE IF EXISTS test_table")



