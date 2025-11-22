# Руководство по тестированию ClickHouse

## Обзор

Тестовая инфраструктура включает автоматический запуск ClickHouse контейнера через Docker Compose. Все тесты могут использовать `clickhouse_client` фиксчуру для работы с ClickHouse.

## Параметры подключения (тестовая среда)

```
Host: 127.0.0.1
Port: 9001 (Native протокол)
Port: 8124 (HTTP интерфейс)
User: test_user
Password: test_password
Database: test_db
```

## Фиксчуры

### clickhouse_client

AsyncClient для ClickHouse. Переиспользует session-scoped подключение для оптимизации.

**Область видимости (scope):** `function` - создаётся для каждого теста, но использует общее session-scoped подключение

**Тип:** `AsyncClient` из `clickhouse_connect.driver.asyncclient`

## Примеры использования

### 1. Простой запрос SELECT

```python
@pytest.mark.asyncio
async def test_simple_query(clickhouse_client):
    result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

### 2. Создание таблицы и вставка данных

```python
@pytest.mark.asyncio
async def test_create_and_insert(clickhouse_client):
    # Создание таблицы
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_users (
            id UInt32,
            name String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    
    # Вставка данных
    await clickhouse_client.insert(
        "test_users",
        [[1, "Alice"], [2, "Bob"]],
        column_names=["id", "name"]
    )
    
    # Проверка данных
    result = await clickhouse_client.query("SELECT COUNT(*) FROM test_users")
    assert result.result_rows[0][0] == 2
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS test_users")
```

### 3. Использование с реальными методами приложения

```python
@pytest.mark.asyncio
async def test_with_real_module(clickhouse_client, monkeypatch):
    # Подменяем глобальный get_clickhouse_client на наш тестовый
    async def mock_get_client():
        return clickhouse_client
    
    monkeypatch.setattr(
        "app.utils.click_house.client.get_clickhouse_client",
        mock_get_client
    )
    
    # Теперь ваш модуль будет использовать тестовый ClickHouse
    from app.modules.my_module import some_function
    result = await some_function()
    assert result is not None
```

### 4. Работа с batch insert

```python
@pytest.mark.asyncio
async def test_batch_insert(clickhouse_client):
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS events (
            timestamp DateTime,
            event_type String,
            user_id UInt32
        ) ENGINE = MergeTree()
        ORDER BY timestamp
    """)
    
    # Вставка множества строк
    data = [
        ["2024-01-01 10:00:00", "login", 1],
        ["2024-01-01 10:01:00", "click", 1],
        ["2024-01-01 10:02:00", "logout", 1],
    ]
    
    await clickhouse_client.insert(
        "events",
        data,
        column_names=["timestamp", "event_type", "user_id"]
    )
    
    # Проверка
    result = await clickhouse_client.query("SELECT COUNT(*) FROM events WHERE event_type = 'click'")
    assert result.result_rows[0][0] == 1
```

### 5. Работа с агрегирующими функциями

```python
@pytest.mark.asyncio
async def test_aggregate_functions(clickhouse_client):
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS metrics (
            metric_name String,
            value Float32
        ) ENGINE = MergeTree()
        ORDER BY metric_name
    """)
    
    data = [
        ["cpu", 45.5],
        ["cpu", 52.3],
        ["memory", 78.9],
        ["memory", 81.2],
    ]
    
    await clickhouse_client.insert(
        "metrics",
        data,
        column_names=["metric_name", "value"]
    )
    
    result = await clickhouse_client.query("""
        SELECT metric_name, AVG(value) as avg_value
        FROM metrics
        GROUP BY metric_name
        ORDER BY metric_name
    """)
    
    assert len(result.result_rows) == 2
    assert result.result_rows[0][0] == "cpu"
```

## Лучшие практики

### 1. Очищайте за собой

Всегда удаляйте созданные таблицы в конце теста:

```python
@pytest.mark.asyncio
async def test_something(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE ... ")
    # Ваш тест
    await clickhouse_client.command("DROP TABLE IF EXISTS table_name")
```

### 2. Используйте `IF NOT EXISTS` и `IF EXISTS`

```python
# CREATE
await clickhouse_client.command("CREATE TABLE IF NOT EXISTS ...")

# DROP
await clickhouse_client.command("DROP TABLE IF EXISTS ...")
```

### 3. Используйте фикстуры для переиспользования кода

```python
@pytest.fixture
async def test_table(clickhouse_client):
    """Фиксчура для создания и очистки тестовой таблицы"""
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_data (
            id UInt32,
            value String
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    
    yield clickhouse_client
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS test_data")

@pytest.mark.asyncio
async def test_with_fixture(test_table):
    result = await test_table.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

### 4. Используйте правильные типы данных

```python
# Правильно - ClickHouse типы
CREATE TABLE data (
    id UInt32,              # Беззнаковое целое
    count Int32,            # Знаковое целое
    price Decimal(10, 2),   # Число с фиксированной точкой
    name String,            # Строка
    created_at DateTime,    # Дата и время
    tags Array(String)      # Массив строк
)
```

## Отладка

### Проверка статуса подключения

```python
@pytest.mark.asyncio
async def test_clickhouse_status(clickhouse_client):
    result = await clickhouse_client.query("SELECT version()")
    print(f"ClickHouse version: {result.result_rows[0][0]}")
```

### Просмотр всех таблиц

```python
@pytest.mark.asyncio
async def test_list_tables(clickhouse_client):
    result = await clickhouse_client.query(
        "SELECT name FROM system.tables WHERE database = currentDatabase()"
    )
    tables = [row[0] for row in result.result_rows]
    print(f"Tables: {tables}")
```

### Проверка размера таблицы

```python
@pytest.mark.asyncio
async def test_table_size(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE test (id UInt32) ENGINE = MergeTree() ORDER BY id")
    
    result = await clickhouse_client.query("""
        SELECT formatReadableSize(bytes_on_disk) 
        FROM system.tables 
        WHERE name = 'test'
    """)
    
    print(f"Table size: {result.result_rows[0][0]}")
```

## Docker Compose конфигурация

ClickHouse контейнер запускается через `docker-compose.test.yml`:

```yaml
test_clickhouse:
  image: clickhouse/clickhouse-server:latest
  environment:
    CLICKHOUSE_DB: test_db
    CLICKHOUSE_USER: test_user
    CLICKHOUSE_PASSWORD: test_password
  ports:
    - "8124:8123"  # HTTP интерфейс
    - "9001:9000"  # Native протокол
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
    interval: 5s
    timeout: 5s
    retries: 5
```

## Решение проблем

### Проблема: "Connection refused"

**Решение:** Убедитесь, что Docker контейнер запущен:

```bash
docker compose -f tests/docker-compose.test.yml ps
```

### Проблема: "Cannot connect to database test_db"

**Решение:** Проверьте, что база данных создана правильно:

```bash
docker compose -f tests/docker-compose.test.yml exec test_clickhouse clickhouse-client -u test_user --password test_password -d test_db
```

### Проблема: "Table already exists"

**Решение:** Используйте `DROP TABLE IF EXISTS` перед созданием:

```python
await clickhouse_client.command("DROP TABLE IF EXISTS table_name")
await clickhouse_client.command("CREATE TABLE ...")
```

## Ссылки

- [ClickHouse Python Driver](https://github.com/ClickHouse/clickhouse-connect)
- [ClickHouse SQL Reference](https://clickhouse.com/docs/en/sql-reference)
- [Docker Hub ClickHouse](https://hub.docker.com/r/clickhouse/clickhouse-server)



