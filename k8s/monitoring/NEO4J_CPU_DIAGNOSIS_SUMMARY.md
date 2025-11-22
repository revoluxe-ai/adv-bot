# 🔍 Итоги диагностики CPU Neo4j

## ✅ Что работает правильно

1. **CPU Quota (cgroup v2):** 4 CPU доступно (400000 / 100000)
2. **Kubernetes ресурсы:** limits = requests = 4 CPU
3. **JVM:** Нет ограничений ActiveProcessorCount
4. **Контейнер видит:** 26 CPU (все CPU ноды)

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА

### Причина использования только 1 CPU

**Код в `app/utils/NeoDataScience/driver.py:633-659`:**

```python
async def _update_items_vectors_in_redis(self) -> None:
    # ОДИН большой запрос - загружает ВСЕ векторы сразу
    query = """
    MATCH (item:Item)
    WHERE item.fastrp IS NOT NULL
    RETURN item.nmid as nmid, item.fastrp as vector
    """
    
    # Выполняется в ОДНОЙ транзакции
    records = await session.execute_read(get_items_vectors, query)
    
    # Обработка ВСЕХ записей ПОСЛЕДОВАТЕЛЬНО
    for record in records:
        await redis_manager.set_item_vector(record["nmid"], record["vector"])
```

**Почему используется только 1 CPU:**

1. **Один запрос = один worker thread** в Neo4j
2. **Нет параллельных запросов** - приложение отправляет один запрос
3. **Последовательная обработка** - даже если запрос быстрый, результаты обрабатываются по одной записи

### Neo4j worker_count не поможет!

**Настройка `dbms.threads.worker_count` работает только если:**
- Есть **несколько параллельных клиентов/запросов**
- Запросы **разделены на батчи**
- Используются **параллельные процедуры GDS**

**Если приложение отправляет один запрос** → Neo4j использует один worker thread → один CPU

## 🛠️ РЕШЕНИЕ

### Вариант 1: Разделить запрос на параллельные батчи (РЕКОМЕНДУЕТСЯ)

```python
async def _update_items_vectors_in_redis(self) -> None:
    # Сначала получить общее количество
    count_query = "MATCH (item:Item) WHERE item.fastrp IS NOT NULL RETURN count(item) as total"
    total = await self._get_count(count_query)
    
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
    
    # Запустить 4 параллельных запроса = 4 CPU
    tasks = [load_batch(i * batch_size) for i in range(num_batches)]
    await asyncio.gather(*tasks[:4])  # Ограничить до 4 параллельных запросов
```

### Вариант 2: Параллельная обработка результатов

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
    
    # Обработать батчи параллельно (4 параллельных обработчика = 4 CPU)
    semaphore = asyncio.Semaphore(4)
    async def process_with_limit(batch):
        async with semaphore:
            await process_batch(batch)
    
    await asyncio.gather(*[process_with_limit(batch) for batch in batches])
```

## 📊 Ожидаемый результат

После применения решения:
- ✅ Neo4j будет использовать **2-4 CPU** вместо 1
- ✅ Загрузка векторов ускорится в **2-4 раза**
- ✅ Прогнозирование CTR будет работать быстрее

## 🎯 Вывод

**Проблема НЕ в конфигурации Neo4j**, а в **архитектуре запросов**:
- ❌ Один большой запрос → один CPU
- ✅ Несколько параллельных запросов → несколько CPU

**Настройки Neo4j (`dbms.threads.worker_count`) не помогут**, если приложение отправляет один запрос. Нужно изменить код для параллельной обработки.

---

**Дата:** 2025-11-18  
**Статус:** Проблема найдена, требуется изменение кода





