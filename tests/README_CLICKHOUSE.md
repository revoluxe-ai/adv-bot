# ClickHouse тестирование

Полная документация и примеры для использования ClickHouse в тестах.

## 📚 Документация

| Файл | Описание |
|------|----------|
| [QUICKSTART_CLICKHOUSE.md](QUICKSTART_CLICKHOUSE.md) | 🚀 **Начните отсюда** - 30 секунд, 3 примера |
| [CLICKHOUSE_TESTING_GUIDE.md](CLICKHOUSE_TESTING_GUIDE.md) | 📖 Полное руководство с 5+ примерами и best practices |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 🔄 Как переписать существующие тесты на ClickHouse |
| [test_clickhouse_session_smoke.py](test_clickhouse_session_smoke.py) | 💡 Готовые примеры тестов |

## ⚡ Быстрый старт

```python
import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient

@pytest.mark.asyncio
async def test_example(clickhouse_client: AsyncClient):
    # Создание таблицы
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test (id UInt32) ENGINE = MergeTree() ORDER BY id
    """)
    
    # Вставка данных
    await clickhouse_client.insert("test", [[1]], ["id"])
    
    # Проверка
    result = await clickhouse_client.query("SELECT COUNT(*) FROM test")
    assert result.result_rows[0][0] == 1
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS test")
```

## 🔧 Основная фиксчура

### `clickhouse_client` (function-scope)

Async клиент для ClickHouse, готов к использованию в тестах.

**Параметры подключения:**
- Host: `127.0.0.1`
- Port: `9001` (Native protocol)
- User: `test_user`
- Password: `test_password`
- Database: `test_db`

**Основные методы:**
```python
# SELECT запрос
result = await clickhouse_client.query("SELECT * FROM table")

# CREATE, DROP, ALTER
await clickhouse_client.command("CREATE TABLE ...")

# INSERT
await clickhouse_client.insert("table_name", [[row1], [row2]], ["col1", "col2"])
```

## 📝 Примеры по сложности

### Уровень 1: Минимальный
```python
@pytest.mark.asyncio
async def test_minimal(clickhouse_client):
    result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

### Уровень 2: Работа с таблицей
```python
@pytest.mark.asyncio
async def test_with_table(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE test (id UInt32) ENGINE = MergeTree() ORDER BY id")
    await clickhouse_client.insert("test", [[1]], ["id"])
    result = await clickhouse_client.query("SELECT COUNT(*) FROM test")
    assert result.result_rows[0][0] == 1
    await clickhouse_client.command("DROP TABLE test")
```

### Уровень 3: С фиксчурой
```python
@pytest.fixture
async def test_table(clickhouse_client):
    await clickhouse_client.command("CREATE TABLE test ...")
    yield clickhouse_client
    await clickhouse_client.command("DROP TABLE test")

@pytest.mark.asyncio
async def test_with_fixture(test_table):
    # test_table это готовый clickhouse_client с созданной таблицей
    result = await test_table.query("SELECT ...")
```

### Уровень 4: Интеграционный тест
```python
@pytest.mark.asyncio
async def test_integration(clickhouse_client):
    # Создание нескольких таблиц
    await clickhouse_client.command("CREATE TABLE events ...")
    await clickhouse_client.command("CREATE TABLE stats ...")
    
    # Заполнение данными
    await clickhouse_client.insert("events", data_events, columns_events)
    
    # Тест функции, которая работает с ClickHouse
    result = await my_clickhouse_function(clickhouse_client)
    
    # Проверка результата
    assert result.processed_events == 100
    
    # Очистка
    await clickhouse_client.command("DROP TABLE events")
    await clickhouse_client.command("DROP TABLE stats")
```

## 🏗️ Архитектура

```
pytest
  ↓
conftest.py
  ├── setup_test_database() [session-scope]
  │   ├── Docker Compose up (PostgreSQL + ClickHouse)
  │   ├── Ожидание PostgreSQL (5433)
  │   └── Ожидание ClickHouse (9001, 8124)
  │
  ├── clickhouse_client_session [session-scope]
  │   └── AsyncClient (переиспользуется)
  │
  └── clickhouse_client [function-scope] ← ВСЕ ТЕСТЫ ИСПОЛЬЗУЮТ ЭТО
      └── Зависит от clickhouse_client_session
```

## 🚀 Запуск тестов

```bash
# Все тесты
pytest tests/

# Smoke тесты (проверка подключения)
pytest tests/test_clickhouse_session_smoke.py -v

# Конкретный тест
pytest tests/test_clickhouse_session_smoke.py::test_clickhouse_session_smoke -v

# С выводом логов
pytest tests/ -s

# С очень подробным выводом
pytest tests/ -vv --tb=short
```

## 🐛 Диагностика

### Проверка статуса контейнеров
```bash
docker compose -f tests/docker-compose.test.yml ps
```

### Просмотр логов ClickHouse
```bash
docker compose -f tests/docker-compose.test.yml logs test_clickhouse
```

### Подключение к ClickHouse вручную
```bash
docker compose -f tests/docker-compose.test.yml exec test_clickhouse \
  clickhouse-client -u test_user --password test_password -d test_db
```

### Проверка версии ClickHouse
```bash
docker compose -f tests/docker-compose.test.yml exec test_clickhouse \
  clickhouse-client -u test_user --password test_password -q "SELECT version()"
```

## 📊 Конфигурация Docker

Контейнер ClickHouse определён в `docker-compose.test.yml`:

```yaml
test_clickhouse:
  image: clickhouse/clickhouse-server:latest
  environment:
    CLICKHOUSE_DB: test_db
    CLICKHOUSE_USER: test_user
    CLICKHOUSE_PASSWORD: test_password
  ports:
    - "8124:8123"  # HTTP
    - "9001:9000"  # Native
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
    interval: 5s
    timeout: 5s
    retries: 5
```

## ✅ Чек-лист для нового теста

- [ ] Добавить параметр `clickhouse_client` в функцию
- [ ] Создать таблицу(ы) с помощью `command()`
- [ ] Заполнить данные с помощью `insert()`
- [ ] Написать основную логику теста
- [ ] Добавить проверки `assert`
- [ ] Удалить таблицы с помощью `command("DROP TABLE")`
- [ ] Запустить тест: `pytest tests/your_test.py -v`

## 🔗 Связанные документы

- [conftest.py](../conftest.py) - Основной файл конфигурации (см. фиксчуры clickhouse_client)
- [../CLICKHOUSE_TEST_SETUP_SUMMARY.md](../CLICKHOUSE_TEST_SETUP_SUMMARY.md) - Резюме что было сделано
- [../docker-compose.test.yml](../docker-compose.test.yml) - Docker конфигурация

## 📚 Дополнительные ресурсы

- [ClickHouse SQL Reference](https://clickhouse.com/docs/en/sql-reference)
- [ClickHouse Python Driver](https://github.com/ClickHouse/clickhouse-connect)
- [Docker Hub - ClickHouse](https://hub.docker.com/r/clickhouse/clickhouse-server)

## 🎯 Типичные задачи

### Задача: Тестировать функцию, которая читает из ClickHouse
```python
@pytest.mark.asyncio
async def test_get_stats(clickhouse_client):
    # 1. Подготовка: создаём таблицу
    await clickhouse_client.command("CREATE TABLE stats ...")
    
    # 2. Заполнение: добавляем тестовые данные
    await clickhouse_client.insert("stats", test_data, columns)
    
    # 3. Тест: вызываем функцию
    result = await get_stats(clickhouse_client)
    
    # 4. Проверка: верифицируем результат
    assert result == expected
    
    # 5. Очистка: удаляем таблицу
    await clickhouse_client.command("DROP TABLE stats")
```

### Задача: Тестировать функцию, которая пишет в ClickHouse
```python
@pytest.mark.asyncio
async def test_save_stats(clickhouse_client):
    # 1. Подготовка
    await clickhouse_client.command("CREATE TABLE stats ...")
    
    # 2. Тест
    await save_stats(clickhouse_client, new_data)
    
    # 3. Проверка
    result = await clickhouse_client.query("SELECT * FROM stats")
    assert len(result.result_rows) == expected_count
    
    # 4. Очистка
    await clickhouse_client.command("DROP TABLE stats")
```

### Задача: Используется async контекстный менеджер
```python
@pytest.mark.asyncio
async def test_with_context_manager(clickhouse_client):
    from app.utils.click_house.client import get_clickhouse_client
    
    # Если в коде используется: async with get_clickhouse_client() as client
    # Вы можете мокировать это или использовать реальный тестовый клиент
    
    # Вариант 1: Использовать реальный клиент напрямую
    await clickhouse_client.command("CREATE TABLE ...")
    result = await your_function(clickhouse_client)
    
    # Вариант 2: Мокировать контекстный менеджер
    from unittest.mock import AsyncMock, patch
    
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = clickhouse_client
    mock_context.__aexit__.return_value = None
    
    with patch("app.utils.click_house.client.get_clickhouse_client", return_value=mock_context):
        result = await your_function()
    
    assert result is not None
```

## 🆘 Решение проблем

| Проблема | Решение |
|----------|---------|
| "Connection refused" | `docker compose -f tests/docker-compose.test.yml ps` |
| "Cannot connect to database" | `docker compose -f tests/docker-compose.test.yml logs test_clickhouse` |
| "Table already exists" | Используйте `CREATE TABLE IF NOT EXISTS` |
| "Таблица не удаляется" | Используйте `DROP TABLE IF EXISTS` |
| Тест медленный | Используйте `ORDER BY` в CREATE TABLE для MergeTree |

---

**Начните с:** [QUICKSTART_CLICKHOUSE.md](QUICKSTART_CLICKHOUSE.md) 🚀



