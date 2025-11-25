# Быстрый старт: тестирование с ClickHouse

## За 30 секунд

Вот минимальный код для использования ClickHouse в тестах:

```python
import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient

@pytest.mark.asyncio
async def test_simple(clickhouse_client: AsyncClient):
    # Простой запрос
    result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

## Типичная задача: создание таблицы и вставка данных

```python
@pytest.mark.asyncio
async def test_with_table(clickhouse_client: AsyncClient):
    # Создание
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS users (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    
    # Вставка
    await clickhouse_client.insert(
        "users",
        [[1, "Alice"], [2, "Bob"]],
        column_names=["id", "name"]
    )
    
    # Проверка
    result = await clickhouse_client.query("SELECT COUNT(*) FROM users")
    assert result.result_rows[0][0] == 2
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS users")
```

## Основные методы

| Метод | Описание | Пример |
|-------|---------|--------|
| `query(sql)` | SELECT запрос | `await client.query("SELECT * FROM table")` |
| `command(sql)` | DDL (CREATE, DROP, ALTER) | `await client.command("CREATE TABLE ...")` |
| `insert(table, data, columns)` | Вставка данных | `await client.insert("table", [[1, "a"]], ["id", "name"])` |

## Три варианта использования

### 1. Минимальный (только фиксчура)
```python
@pytest.mark.asyncio
async def test_minimal(clickhouse_client):
    result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

### 2. С таблицей (самый частый случай)
```python
@pytest.mark.asyncio
async def test_with_data(clickhouse_client):
    # Подготовка
    await clickhouse_client.command("CREATE TABLE ... ")
    
    # Ваш тест
    result = await clickhouse_client.query("SELECT ...")
    assert ...
    
    # Очистка
    await clickhouse_client.command("DROP TABLE ...")
```

### 3. С фиксчурой (для повторного использования)
```python
@pytest.fixture
async def users_table(clickhouse_client):
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS users (id UInt32, name String)
        ENGINE = MergeTree() ORDER BY id
    """)
    yield clickhouse_client
    await clickhouse_client.command("DROP TABLE IF EXISTS users")

@pytest.mark.asyncio
async def test_with_fixture(users_table):
    await users_table.insert("users", [[1, "Alice"]], ["id", "name"])
    result = await users_table.query("SELECT COUNT(*) FROM users")
    assert result.result_rows[0][0] == 1
```

## Запуск тестов

```bash
# Все тесты
pytest tests/

# Конкретный файл
pytest tests/test_clickhouse_session_smoke.py

# С выводом
pytest tests/ -v

# С логами
pytest tests/ -s

# Конкретный тест
pytest tests/test_clickhouse_session_smoke.py::test_clickhouse_session_smoke
```

## Типичные ошибки

### ❌ Забыли DROP TABLE
```python
# Плохо - таблица остаётся и может помешать следующим тестам
async def test_bad(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE test ...")
    # тест...
```

### ✅ Правильно - DROP в конце
```python
# Хорошо - таблица удаляется после теста
async def test_good(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE test ...")
    try:
        # тест...
    finally:
        await clickhouse_client.command("DROP TABLE IF EXISTS test")
```

## Подключение к тестовому ClickHouse вручную

```bash
docker compose -f tests/docker-compose.test.yml exec test_clickhouse \
  clickhouse-client -u test_user --password test_password -d test_db
```

Или через HTTP:
```bash
curl -u test_user:test_password http://localhost:8124/?query=SELECT%201
```

## Дополнительно

- Полное руководство: `tests/CLICKHOUSE_TESTING_GUIDE.md`
- Примеры: `tests/test_clickhouse_session_smoke.py`
- Настройка: `conftest.py` (строки с "clickhouse")
- Docker config: `tests/docker-compose.test.yml`



