# 🔍 Результаты диагностики CPU Neo4j

## 📋 Дата проверки
2025-11-18

## ✅ Что проверено

### 1. Видимость CPU внутри контейнера
- **nproc:** 26 CPU (видит все CPU ноды)
- **lscpu:** 26 CPU cores, 1 thread per core
- ✅ Контейнер видит достаточно CPU

### 2. Kubernetes ресурсы
- **Limits:** 4 CPU, 16Gi memory
- **Requests:** 4 CPU, 16Gi memory
- ✅ Ресурсы настроены правильно

### 3. JVM параметры
- **ActiveProcessorCount:** Не найден (OK)
- ✅ JVM не ограничивает количество CPU

### 4. Текущее использование CPU
- **Текущее:** 1520m (1.5 CPU)
- **Ранее:** 969m (1 CPU)
- ⚠️ Используется только ~38% от доступных 4 CPU

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА

### Причина низкого использования CPU

**Код в `app/utils/NeoDataScience/driver.py:633-659`:**

```python
async def _update_items_vectors_in_redis(self) -> None:
    query = """
    MATCH (item:Item)
    WHERE item.fastrp IS NOT NULL
    RETURN item.nmid as nmid, item.fastrp as vector
    """
    
    async with neo4j.AsyncGraphDatabase.driver(...) as driver:
        async with driver.session() as session:
            records = await session.execute_read(get_items_vectors, query)
    
    # Обработка ВСЕХ записей последовательно
    for record in records:
        nmid = record["nmid"]
        vector = record["vector"]
        await redis_manager.set_item_vector(nmid, vector)
```

**Проблемы:**

1. **Один большой запрос** - загружает ВСЕ векторы сразу
2. **Последовательная обработка** - `for record in records:` обрабатывает записи по одной
3. **Одна транзакция** - весь запрос выполняется в одной транзакции
4. **Нет параллелизма** - Neo4j не может использовать несколько CPU для одного запроса

### Почему Neo4j использует только 1 CPU?

1. **Один запрос = один worker thread** - Neo4j выполняет один запрос в основном потоке
2. **Нет параллельных запросов** - если приложение отправляет один запрос, Neo4j использует только один CPU
3. **Последовательная обработка результатов** - даже если запрос быстрый, обработка результатов происходит последовательно

## 🛠️ РЕШЕНИЕ

### Вариант 1: Параллельная обработка результатов (быстрое решение)

Разделить обработку результатов на батчи и обрабатывать параллельно:

```python
async def _update_items_vectors_in_redis(self) -> None:
    query = """
    MATCH (item:Item)
    WHERE item.fastrp IS NOT NULL
    RETURN item.nmid as nmid, item.fastrp as vector
    """
    
    async with neo4j.AsyncGraphDatabase.driver(...) as driver:
        async with driver.session() as session:
            records = await session.execute_read(get_items_vectors, query)
    
    # Разделить на батчи и обработать параллельно
    batch_size = 1000
    batches = [records[i:i+batch_size] for i in range(0, len(records), batch_size)]
    
    async def process_batch(batch):
        for record in batch:
            await redis_manager.set_item_vector(record["nmid"], record["vector"])
    
    # Обработать батчи параллельно
    await asyncio.gather(*[process_batch(batch) for batch in batches])
```

### Вариант 2: Разделить запрос на несколько параллельных запросов (лучшее решение)

Использовать `SKIP` и `LIMIT` для параллельной загрузки:

```python
async def _update_items_vectors_in_redis(self) -> None:
    # Сначала получить общее количество
    count_query = "MATCH (item:Item) WHERE item.fastrp IS NOT NULL RETURN count(item) as total"
    total = await self._get_count(count_query)
    
    # Разделить на параллельные запросы
    batch_size = 10000
    num_batches = (total + batch_size - 1) // batch_size
    
    async def load_batch(skip: int):
        query = f"""
        MATCH (item:Item)
        WHERE item.fastrp IS NOT NULL
        RETURN item.nmid as nmid, item.fastrp as vector
        SKIP {skip} LIMIT {batch_size}
        """
        async with neo4j.AsyncGraphDatabase.driver(...) as driver:
            async with driver.session() as session:
                records = await session.execute_read(get_items_vectors, query)
                for record in records:
                    await redis_manager.set_item_vector(record["nmid"], record["vector"])
    
    # Запустить параллельные запросы
    tasks = [load_batch(i * batch_size) for i in range(num_batches)]
    await asyncio.gather(*tasks)
```

### Вариант 3: Использовать GDS для параллельной обработки

Если используется Graph Data Science, можно использовать параллельные процедуры:

```cypher
CALL gds.beta.graph.streamNodeProperties(
  'myGraph',
  ['fastrp'],
  { nodeLabels: ['Item'] }
)
YIELD nodeId, nodeProperties
RETURN nodeId, nodeProperties.fastrp as vector
```

## 📊 Ожидаемый результат

После применения решения:
- ✅ Neo4j будет использовать **2-4 CPU** вместо 1
- ✅ Загрузка векторов ускорится в **2-4 раза**
- ✅ Общая производительность системы улучшится

## 🎯 Вывод

**Проблема НЕ в конфигурации Neo4j**, а в **способе выполнения запросов**:
- Один большой запрос → один CPU
- Несколько параллельных запросов → несколько CPU

**Настройки `dbms.threads.worker_count` помогут только если:**
- Есть несколько параллельных клиентов/запросов
- Запросы разделены на батчи
- Используются параллельные процедуры GDS

---

**Статус:** Проблема найдена, требуется изменение кода для параллельной обработки





