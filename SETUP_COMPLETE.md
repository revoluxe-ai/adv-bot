# ✅ Тестовая сессия ClickHouse настроена

## 🎉 Что было сделано

Была полностью настроена тестовая инфраструктура для ClickHouse по аналогии с PostgreSQL.

### 📝 Файлы, которые были изменены:

```
✅ conftest.py
   ├── Добавлены константы подключения TEST_CLICKHOUSE_*
   ├── Добавлены фиксчуры:
   │   ├── clickhouse_client_session (session-scope, переиспользуется)
   │   └── clickhouse_client (function-scope, для каждого теста)
   ├── Обновлена setup_test_database():
   │   ├── Ожидание PostgreSQL контейнера
   │   ├── Ожидание ClickHouse контейнера ← НОВОЕ
   │   └── Graceful shutdown обоих контейнеров
   └── Добавлена документация в docstrings

✅ tests/docker-compose.test.yml
   ├── test_db (PostgreSQL 15)
   └── test_clickhouse ← НОВОЕ
       ├── ClickHouse latest
       ├── Порты: 8124 (HTTP), 9001 (Native)
       ├── Credentials: test_user / test_password
       └── Database: test_db

✅ tests/test_clickhouse_session_smoke.py [НОВЫЙ]
   ├── test_clickhouse_session_smoke() - базовая проверка
   └── test_clickhouse_create_table() - пример CREATE/INSERT

📚 ДОКУМЕНТАЦИЯ (НОВАЯ):

✅ tests/README_CLICKHOUSE.md
   └── Главный файл с ссылками на все документы

✅ tests/QUICKSTART_CLICKHOUSE.md
   ├── 30-секундный старт
   ├── 3 типичных задачи
   ├── Основные методы
   └── Команды запуска

✅ tests/CLICKHOUSE_TESTING_GUIDE.md
   ├── Полное руководство
   ├── 5+ примеров с кодом
   ├── Лучшие практики
   ├── Отладка
   └── Решение проблем

✅ tests/MIGRATION_GUIDE.md
   ├── Как переписать существующие тесты
   ├── 4 сценария миграции
   ├── Типичные таблицы
   └── Чек-листы

✅ CLICKHOUSE_TEST_SETUP_SUMMARY.md
   └── Техническое резюме что было сделано

✅ SETUP_COMPLETE.md
   └── Этот файл
```

## 🚀 Использование

### Минимальный пример:
```python
@pytest.mark.asyncio
async def test_clickhouse(clickhouse_client):
    result = await clickhouse_client.query("SELECT 1")
    assert result.result_rows[0][0] == 1
```

### Типичный пример:
```python
@pytest.mark.asyncio
async def test_with_data(clickhouse_client):
    # Создание таблицы
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS users (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
    """)
    
    # Вставка данных
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

## 📊 Параметры подключения (тестовая среда)

| Параметр | Значение |
|----------|----------|
| Host | 127.0.0.1 |
| Port (Native) | 9001 |
| Port (HTTP) | 8124 |
| User | test_user |
| Password | test_password |
| Database | test_db |

## 🏗️ Архитектура

```
pytest execution
    ↓
conftest.py::setup_test_database (session-scope)
    ↓
docker-compose up -d (PostgreSQL + ClickHouse)
    ↓
┌─────────────────────────────────────────────┐
│  Ожидание PostgreSQL (max 30 попыток)      │
│  Ожидание ClickHouse (max 30 попыток)      │
│  Создание таблиц, миграции                 │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│  clickhouse_client_session (session-scope)     │
│  AsyncClient (переиспользуется для всех тестов)│
└─────────────────────────────────────────────────┘
    ↓
    │  Каждый тест
    │
    ├─ clickhouse_client (function-scope) ← ИСПОЛЬЗУЕТСЯ В ТЕСТАХ
    │  └─ Использует clickhouse_client_session
    │
    └─ async_session (function-scope)
       └─ Использует async_engine (PostgreSQL)

    ↓
docker-compose down (Graceful shutdown)
```

## 🧪 Тестирование

### Запуск smoke тестов (проверка подключения)
```bash
pytest tests/test_clickhouse_session_smoke.py -v
```

### Запуск всех тестов
```bash
pytest tests/ -v
```

### Запуск с логами
```bash
pytest tests/ -v -s
```

## 📚 Документация по порядку важности

1. **[tests/README_CLICKHOUSE.md](tests/README_CLICKHOUSE.md)** 📖 - Главный обзор, начните с этого
2. **[tests/QUICKSTART_CLICKHOUSE.md](tests/QUICKSTART_CLICKHOUSE.md)** 🚀 - Для нетерпеливых (30 сек)
3. **[tests/CLICKHOUSE_TESTING_GUIDE.md](tests/CLICKHOUSE_TESTING_GUIDE.md)** 📚 - Полное руководство
4. **[tests/MIGRATION_GUIDE.md](tests/MIGRATION_GUIDE.md)** 🔄 - Для переписи старых тестов
5. **[CLICKHOUSE_TEST_SETUP_SUMMARY.md](CLICKHOUSE_TEST_SETUP_SUMMARY.md)** 🔧 - Техническое резюме

## ⚡ Быстрые команды

### Запуск контейнеров вручную
```bash
cd tests
docker-compose -f docker-compose.test.yml up -d
```

### Проверка статуса
```bash
cd tests
docker-compose -f docker-compose.test.yml ps
```

### Подключение к ClickHouse
```bash
cd tests
docker-compose -f docker-compose.test.yml exec test_clickhouse clickhouse-client -u test_user --password test_password -d test_db
```

### Просмотр логов
```bash
cd tests
docker-compose -f docker-compose.test.yml logs test_clickhouse
```

### Остановка контейнеров
```bash
cd tests
docker-compose -f docker-compose.test.yml down -v
```

## 🔗 Фиксчуры

### `clickhouse_client` (function-scope)
```python
@pytest.mark.asyncio
async def test_example(clickhouse_client: AsyncClient):
    # Используйте clickhouse_client
    result = await clickhouse_client.query("SELECT 1")
```

**Методы:**
- `query(sql)` - SELECT запросы
- `command(sql)` - CREATE, DROP, ALTER команды
- `insert(table, data, columns)` - Вставка данных

### `async_session` (function-scope, PostgreSQL)
```python
@pytest.mark.asyncio
async def test_postgres(async_session: AsyncSession):
    # PostgreSQL сессия (как и было раньше)
    result = await async_session.execute(text("SELECT 1"))
```

## 🎯 Примеры для часто встречающихся модулей

### Для app/modules/shop_runner/service_manager/services/keyword_stamp_manager/click_house_manager/

```python
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.click_house_manager import ClickHouseManager

@pytest.mark.asyncio
async def test_keyword_stamp_manager(clickhouse_client):
    manager = ClickHouseManager(clickhouse_client)
    
    # Создание таблицы со статистикой
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS stamps (
            keyword String,
            timestamp DateTime,
            position UInt32
        ) ENGINE = MergeTree()
        ORDER BY timestamp
    """)
    
    # Ваш тест
    result = await manager.get_stamps("test_keyword")
    assert result is not None
    
    # Очистка
    await clickhouse_client.command("DROP TABLE IF EXISTS stamps")
```

## ✅ Чек-лист перед запуском тестов

- [ ] Установлены зависимости: `poetry install`
- [ ] Docker установлен и запущен
- [ ] Docker Compose установлен
- [ ] Порты 5433, 8124, 9001 свободны
- [ ] Переменные окружения установлены (.env файл)

## 🆘 Решение проблем

### "Connection refused"
```bash
docker ps -a  # Проверить, что контейнеры запущены
docker logs test_clickhouse  # Просмотреть логи
```

### "Table already exists"
Используйте `IF NOT EXISTS`:
```python
await clickhouse_client.command("CREATE TABLE IF NOT EXISTS ...")
```

### "Cannot connect to database test_db"
```bash
docker-compose -f tests/docker-compose.test.yml exec test_clickhouse \
  clickhouse-client -u test_user --password test_password -d test_db
```

## 🎓 Обучение

1. Прочитайте [tests/QUICKSTART_CLICKHOUSE.md](tests/QUICKSTART_CLICKHOUSE.md) - 5 минут
2. Запустите [tests/test_clickhouse_session_smoke.py](tests/test_clickhouse_session_smoke.py) - 2 минуты
3. Напишите свой первый тест - 10 минут
4. При вопросах смотрите [tests/CLICKHOUSE_TESTING_GUIDE.md](tests/CLICKHOUSE_TESTING_GUIDE.md)

## 🚀 Что дальше

1. **Напишите свой первый тест** для модуля, который использует ClickHouse
2. **Мигрируйте существующие тесты** с мокированием на реальный ClickHouse (см. MIGRATION_GUIDE.md)
3. **Добавьте интеграционные тесты** для сложных сценариев
4. **Оптимизируйте производительность** если нужно

## 📞 Нужна помощь?

- Вопрос "Как использовать?" → [tests/QUICKSTART_CLICKHOUSE.md](tests/QUICKSTART_CLICKHOUSE.md)
- Вопрос "Как это работает?" → [tests/CLICKHOUSE_TESTING_GUIDE.md](tests/CLICKHOUSE_TESTING_GUIDE.md)
- Вопрос "Как переписать мой тест?" → [tests/MIGRATION_GUIDE.md](tests/MIGRATION_GUIDE.md)
- Общий обзор → [tests/README_CLICKHOUSE.md](tests/README_CLICKHOUSE.md)

---

**Status:** ✅ Готово к использованию

**Дата:** November 21, 2025

**Версия ClickHouse:** latest (из docker-compose.test.yml)

**Версия Python:** 3.x (из вашей среды)



