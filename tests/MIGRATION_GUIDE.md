# Миграция существующих тестов на ClickHouse фиксчуру

## Обзор

Если у вас есть тесты, которые используют мок ClickHouse или вообще его не используют, вы можете легко переписать их для использования реальной тестовой базы ClickHouse.

## Сценарий 1: Был мок, нужно использовать реальный ClickHouse

### До (с мокированием)
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_module():
    mock_client = AsyncMock()
    mock_client.query.return_value = {"data": [[1, "test"]]}
    
    with patch("app.utils.click_house.client.get_clickhouse_client", return_value=mock_client):
        result = await my_clickhouse_function()
        assert result == "expected"
```

### После (с реальным ClickHouse)
```python
@pytest.mark.asyncio
async def test_my_module(clickhouse_client):
    # Подготовка данных в реальной БД
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_data (
            id UInt32,
            value String
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    
    await clickhouse_client.insert(
        "test_data",
        [[1, "test"]],
        column_names=["id", "value"]
    )
    
    # Тест с реальной БД
    result = await my_clickhouse_function()
    assert result == "expected"
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS test_data")
```

## Сценарий 2: Был без ClickHouse вообще, нужно добавить

### До (без БД)
```python
@pytest.mark.asyncio
async def test_keyword_analysis():
    keywords = ["ключевое слово", "тест"]
    
    stats = analyze_keywords(keywords)
    assert len(stats) == 2
```

### После (с ClickHouse)
```python
@pytest.mark.asyncio
async def test_keyword_analysis(clickhouse_client):
    # Создаём таблицу со статистикой ключевых слов
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS keyword_stats (
            keyword String,
            impressions UInt32,
            clicks UInt32,
            created_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY keyword
    """)
    
    # Заполняем тестовыми данными
    keywords = ["ключевое слово", "тест"]
    for i, kw in enumerate(keywords):
        await clickhouse_client.insert(
            "keyword_stats",
            [[kw, 100 + i * 10, 5 + i]],
            column_names=["keyword", "impressions", "clicks", "created_at"]
        )
    
    # Тест
    stats = await analyze_keywords(keywords, clickhouse_client)
    assert len(stats) == 2
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS keyword_stats")
```

## Сценарий 3: Использование с DI контейнером

Если ваше приложение использует Dependency Injection, вы можете переопределить зависимость:

```python
@pytest.mark.asyncio
async def test_with_di(clickhouse_client, di_container):
    # Переопределяем ClickHouse клиент в контейнере
    di_container.clickhouse_client.override(clickhouse_client)
    
    # Теперь сервис будет использовать тестовый ClickHouse
    service = di_container.my_service()
    result = await service.some_method()
    
    assert result is not None
```

## Сценарий 4: Тестирование модуля click_house_manager

### Структура ClickHouse manager
```
app/modules/shop_runner/service_manager/services/keyword_stamp_manager/
├── click_house_manager.py
└── click_house_manager/
    └── click_house_manager.py
```

### Пример теста
```python
import pytest
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.click_house_manager import ClickHouseManager

@pytest.mark.asyncio
async def test_clickhouse_manager(clickhouse_client):
    # Создаём manager с тестовым клиентом
    manager = ClickHouseManager(clickhouse_client)
    
    # Подготовка таблиц (если нужно)
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS stamps (
            keyword String,
            timestamp DateTime,
            position UInt32
        ) ENGINE = MergeTree()
        ORDER BY timestamp
    """)
    
    # Тест
    result = await manager.get_stamps("test_keyword")
    assert result is not None
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS stamps")
```

## Чек-лист при миграции

- [ ] Добавить параметр `clickhouse_client` в функцию теста
- [ ] Заменить мок на реальный клиент
- [ ] Создать необходимые таблицы с помощью `CREATE TABLE`
- [ ] Заполнить таблицы тестовыми данными с помощью `insert`
- [ ] Написать основной тест
- [ ] Добавить очистку с помощью `DROP TABLE IF EXISTS`
- [ ] Протестировать: `pytest tests/your_test_file.py -v`

## Полезные команды

### Запуск одного теста с логами
```bash
pytest tests/your_test_file.py::test_function_name -v -s
```

### Запуск с выводом SQL запросов
```bash
pytest tests/your_test_file.py -v --capture=no
```

### Отладка: подключение к ClickHouse во время теста
```python
@pytest.mark.asyncio
async def test_debug(clickhouse_client):
    # Ваш код
    
    # В какой-то момент остановитесь и вручную проверьте данные
    result = await clickhouse_client.query("SELECT * FROM your_table")
    print(f"DEBUG: {result.result_rows}")
    
    # breakpoint()  # Если используете debugger
```

## Типичные таблицы для тестирования

### Таблица статистики ключевых слов
```python
await clickhouse_client.command("""
    CREATE TABLE IF NOT EXISTS keyword_stats (
        shop_id String,
        keyword String,
        impressions UInt32,
        clicks UInt32,
        ctr Float32,
        date Date
    ) ENGINE = MergeTree()
    ORDER BY (date, shop_id, keyword)
""")
```

### Таблица событий
```python
await clickhouse_client.command("""
    CREATE TABLE IF NOT EXISTS events (
        event_id String,
        event_type String,
        user_id UInt32,
        timestamp DateTime,
        properties String
    ) ENGINE = MergeTree()
    ORDER BY timestamp
""")
```

### Таблица метрик
```python
await clickhouse_client.command("""
    CREATE TABLE IF NOT EXISTS metrics (
        metric_name String,
        metric_value Float32,
        timestamp DateTime,
        tags Array(String)
    ) ENGINE = MergeTree()
    ORDER BY timestamp
""")
```

## Лучшие практики

### 1. Используйте фиксчуры для общих таблиц
```python
@pytest.fixture
async def keyword_stats_table(clickhouse_client):
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS keyword_stats (
            shop_id String,
            keyword String,
            impressions UInt32,
            clicks UInt32
        ) ENGINE = MergeTree()
        ORDER BY (shop_id, keyword)
    """)
    yield clickhouse_client
    await clickhouse_client.command("DROP TABLE IF EXISTS keyword_stats")

@pytest.mark.asyncio
async def test_with_shared_table(keyword_stats_table):
    # keyword_stats_table это clickhouse_client с готовой таблицей
    await keyword_stats_table.insert("keyword_stats", [[...]], [...])
```

### 2. Используйте понятные имена таблиц
```python
# ✅ Хорошо
await clickhouse_client.command("CREATE TABLE IF NOT EXISTS test_keyword_stats ...")

# ❌ Плохо
await clickhouse_client.command("CREATE TABLE IF NOT EXISTS t1 ...")
```

### 3. Всегда проверяйте результаты
```python
result = await clickhouse_client.query("SELECT COUNT(*) FROM table")
print(f"Result: {result.result_rows}")  # Дебаг информация

row_count = result.result_rows[0][0]
assert row_count == expected_count
```

## Ссылки

- [ClickHouse SQL Reference](https://clickhouse.com/docs/en/sql-reference)
- [clickhouse-connect Python Driver](https://github.com/ClickHouse/clickhouse-connect)
- Примеры: `tests/test_clickhouse_session_smoke.py`
- Быстрый старт: `tests/QUICKSTART_CLICKHOUSE.md`
- Полное руководство: `tests/CLICKHOUSE_TESTING_GUIDE.md`



