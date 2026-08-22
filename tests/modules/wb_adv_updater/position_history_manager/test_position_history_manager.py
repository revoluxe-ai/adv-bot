from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from clickhouse_connect.driver import AsyncClient

from app.modules.wb_adv_updater.position_history_manager import (
    PositionHistoryManager,
    PositionHistory,
)


# DDL таблицы с правильным типом timestamp (DateTime вместо Float64)
CLUSTERS_ADV_STATS_DDL = """
CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.clusters_adv_stats_test (
    adv_id      UInt32,
    nmid        UInt64,
    wb_category LowCardinality(String),
    norm_query  LowCardinality(String),
    views       UInt32,
    clicks      UInt32,
    ctr         Float64,
    cpm         Float64,
    add_to_cart UInt32,
    orders      UInt32,
    cpc         Float64,
    avr_pos     Float64,
    date        Date,
    spend       Nullable(Float64) DEFAULT NULL,
    timestamp   DateTime default now()
) ENGINE = MergeTree 
PARTITION BY toYYYYMM(date)
ORDER BY (wb_category, nmid, norm_query, date, timestamp)
SETTINGS index_granularity = 8192
"""

pytestmark = pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_get_position_history_returns_positions(clickhouse_client: AsyncClient) -> None:
    """Тест проверяет, что get_position_history возвращает корректный PositionHistory."""
    
    # Пересоздаём таблицу с правильной структурой (timestamp как DateTime)
    await clickhouse_client.command("DROP TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command(CLUSTERS_ADV_STATS_DDL.replace("clusters_adv_stats_test", "clusters_adv_stats"))
    
    # Подготавливаем тестовые данные
    nmid = 123456789
    today = date.today()
    yesterday = today - timedelta(days=1)
    now = datetime.now()
    
    # Создаём записи для двух разных дней и двух разных ключевых слов
    # Колонки: adv_id, nmid, wb_category, norm_query, views, clicks, ctr, cpm, add_to_cart, orders, cpc, avr_pos, date, timestamp
    columns = [
        "adv_id", "nmid", "wb_category", "norm_query", "views", "clicks",
        "ctr", "cpm", "add_to_cart", "orders", "cpc", "avr_pos", "date", "spend", "timestamp",
    ]
    
    rows = [
        # Две записи для "платье летнее" за сегодня - должны усредниться до 6.0
        [1, nmid, "одежда", "платье летнее", 100, 10, 0.1, 50.0, 5, 2, 5.0, 5.0, today, 0.0, now],
        [1, nmid, "одежда", "платье летнее", 100, 10, 0.1, 50.0, 5, 2, 5.0, 7.0, today, 0.0, now],
        # Одна запись для "платье летнее" за вчера
        [1, nmid, "одежда", "платье летнее", 100, 10, 0.1, 50.0, 5, 2, 5.0, 10.0, yesterday, 0.0, now - timedelta(days=1)],
        # Одна запись для "юбка женская" за сегодня
        [1, nmid, "одежда", "юбка женская", 100, 10, 0.1, 50.0, 5, 2, 5.0, 3.0, today, 0.0, now],
        # Запись для другого nmid - не должна попасть в результат
        [1, 999999999, "одежда", "другой товар", 100, 10, 0.1, 50.0, 5, 2, 5.0, 1.0, today, 0.0, now],
    ]
    
    # Вставляем данные в ClickHouse
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.clusters_adv_stats",
        rows,
        column_names=columns,
    )
    
    # Мокируем get_clickhouse_client для использования тестового клиента
    with patch(
        "app.modules.wb_adv_updater.position_history_manager.position_history_manager.get_client"
    ) as get_client_mock:
        cm = AsyncMock()
        cm.__aenter__.return_value = clickhouse_client
        cm.__aexit__.return_value = None
        get_client_mock.return_value = cm
        
        # Вызываем тестируемый метод
        manager = PositionHistoryManager()
        result = await manager.get_position_history(nmid=nmid, last_days=7)
    
    # Проверяем результат
    assert isinstance(result, PositionHistory)
    assert result.nmid == nmid
    
    # Должно быть 3 позиции: 2 для "платье летнее" (за 2 дня) и 1 для "юбка женская"
    assert len(result.positions) == 3
    
    # Проверяем keyword_positions (группировка по тексту)
    keyword_positions = result.keyword_positions
    assert len(keyword_positions) == 2
    
    # Находим позиции для "платье летнее"
    dress_positions = next(
        (kp for kp in keyword_positions if kp.text == "платье летнее"),
        None,
    )
    assert dress_positions is not None
    assert len(dress_positions.positions) == 2
    
    # Проверяем агрегацию - для today должно быть среднее (5.0 + 7.0) / 2 = 6.0
    today_pos = next(
        (p for p in dress_positions.positions if p.datetime == today),
        None,
    )
    assert today_pos is not None
    assert today_pos.position == pytest.approx(6.0, rel=0.01)
    
    # Для yesterday должно быть 10.0
    yesterday_pos = next(
        (p for p in dress_positions.positions if p.datetime == yesterday),
        None,
    )
    assert yesterday_pos is not None
    assert yesterday_pos.position == pytest.approx(10.0, rel=0.01)


@pytest.mark.asyncio
async def test_get_position_history_returns_empty_for_nonexistent_nmid(
    clickhouse_client: AsyncClient,
) -> None:
    """Тест проверяет, что для несуществующего nmid возвращается пустой PositionHistory."""
    
    # Пересоздаём таблицу с правильной структурой
    await clickhouse_client.command("DROP TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_stats")
    await clickhouse_client.command(CLUSTERS_ADV_STATS_DDL.replace("clusters_adv_stats_test", "clusters_adv_stats"))
    
    nonexistent_nmid = 111111111
    
    with patch(
        "app.modules.wb_adv_updater.position_history_manager.position_history_manager.get_client"
    ) as get_client_mock:
        cm = AsyncMock()
        cm.__aenter__.return_value = clickhouse_client
        cm.__aexit__.return_value = None
        get_client_mock.return_value = cm
        
        manager = PositionHistoryManager()
        result = await manager.get_position_history(nmid=nonexistent_nmid, last_days=7)
    
    assert isinstance(result, PositionHistory)
    assert result.nmid == nonexistent_nmid
    assert len(result.positions) == 0
    assert len(result.keyword_positions) == 0

