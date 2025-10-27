# Диагностика инкрементальной статистики

## Проверка консистентности данных

### 1. Проверка суммы дельт vs total

Запускать **раз в неделю** для диагностики целостности данных.

```sql
-- Проверяет, что сумма дельт = разница между max и min total
SELECT
    nmid,
    sum(orders_delta) AS delta_sum,
    max(total_orders) - min(total_orders) AS total_diff,
    abs(delta_sum - total_diff) AS diff
FROM default_db.wb_common_stat_incremental
WHERE timestamp > now() - INTERVAL 1 DAY
GROUP BY nmid
HAVING abs(delta_sum - total_diff) > 1;
```

**Что проверяется:**
- `delta_sum` - сумма всех изменений за день
- `total_diff` - разница между максимальным и минимальным накопленным значением
- Если `diff > 1` - есть проблемы (пропуски, задвоения, WB откатил данные)

**Норма:** Пустой результат (нет расхождений)

**Если есть расхождения:**
1. Проверить логи на предмет отрицательных дельт (WB откатывает)
2. Проверить, нет ли пропусков обновлений (система падала?)
3. Возможна коррекция данных со стороны WB

---

### 2. Проверка отрицательных дельт

```sql
-- Находит случаи, когда WB откатил статистику
SELECT 
    nmid,
    date,
    timestamp,
    orders_delta,
    total_orders
FROM default_db.wb_common_stat_incremental
WHERE orders_delta < 0
  AND timestamp > now() - INTERVAL 7 DAY
ORDER BY timestamp DESC
LIMIT 100;
```

**Что показывает:**
- Случаи, когда WB уменьшил количество заказов
- Обычно это коррекции/отмены заказов

**Норма:** Редкие случаи (1-2% от записей)

---

### 3. Проверка частоты обновлений

```sql
-- Проверяет, обновляются ли данные каждые 5 минут
SELECT 
    nmid,
    toStartOfFiveMinute(timestamp) AS period,
    count() AS updates_count
FROM default_db.wb_common_stat_incremental
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY nmid, period
HAVING updates_count != 1
ORDER BY period DESC;
```

**Норма:** По 1 обновлению каждые 5 минут на nmid

**Если больше:** Задвоение данных (баг парсера)  
**Если меньше:** Пропуски обновлений (система падала, таймаут WB API)

---

### 4. Сравнение старой и новой логики (при миграции)

```sql
-- Сравниваем результаты старой таблицы vs инкрементальной
WITH old_logic AS (
    SELECT 
        nmid,
        argMax(orders, version) AS orders_old
    FROM default_db.wb_common_stat
    WHERE date = today()
    GROUP BY nmid
),
new_logic AS (
    SELECT 
        nmid,
        sum(orders_delta) AS orders_new
    FROM default_db.wb_common_stat_incremental
    WHERE date = today()
    GROUP BY nmid
)
SELECT 
    old_logic.nmid,
    orders_old,
    orders_new,
    orders_old - orders_new AS diff
FROM old_logic
JOIN new_logic ON old_logic.nmid = new_logic.nmid
WHERE abs(orders_old - orders_new) > 0
LIMIT 100;
```

**Применение:** На этапе тестирования включения `use_incremental_stats`

**Норма:** Нет расхождений или расхождения <5% (из-за тайминга обновлений)

---

### 5. Мониторинг производительности

```sql
-- Средний размер батча вставок
SELECT 
    toStartOfHour(timestamp) AS hour,
    count() AS total_inserts,
    countDistinct(nmid) AS unique_nmids,
    total_inserts / unique_nmids AS avg_batch_size
FROM default_db.wb_common_stat_incremental
WHERE timestamp > now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour DESC;
```

**Оптимально:** `avg_batch_size > 100` (батчевая вставка работает)

**Если < 10:** Проблемы с батчингом, много мелких INSERT'ов

---

### 6. Проверка материализованных представлений

```sql
-- Проверяем, что часовые агрегаты совпадают с сырыми данными
WITH raw_data AS (
    SELECT 
        nmid,
        toStartOfHour(timestamp) AS hour,
        sum(orders_delta) AS orders_raw
    FROM default_db.wb_common_stat_incremental
    WHERE timestamp > now() - INTERVAL 24 HOUR
    GROUP BY nmid, hour
),
mv_data AS (
    SELECT 
        nmid,
        hour_start AS hour,
        sumMerge(orders_sum) AS orders_mv
    FROM default_db.wb_common_stat_hourly
    WHERE hour_start > now() - INTERVAL 24 HOUR
    GROUP BY nmid, hour
)
SELECT 
    raw_data.nmid,
    raw_data.hour,
    orders_raw,
    orders_mv,
    orders_raw - orders_mv AS diff
FROM raw_data
LEFT JOIN mv_data ON raw_data.nmid = mv_data.nmid AND raw_data.hour = mv_data.hour
WHERE abs(orders_raw - orders_mv) > 0
LIMIT 50;
```

**Норма:** Нет расхождений

**Если есть:** MV нужно пересоздать с POPULATE

---

## Когда запускать проверки

| Проверка | Частота | Критичность |
|----------|---------|-------------|
| Консистентность дельт | Раз в неделю | Средняя |
| Отрицательные дельты | По требованию | Низкая |
| Частота обновлений | При проблемах | Высокая |
| Сравнение логик | При миграции | Высокая |
| Производительность | Раз в месяц | Средняя |
| Проверка MV | После пересоздания | Высокая |

---

## Автоматизация (опционально)

Можно добавить в cron или monitoring систему:

```python
# app/utils/diagnostics/incremental_stats_checker.py
async def check_data_consistency() -> dict:
    """Проверяет консистентность инкрементальных данных"""
    async with get_clickhouse_client() as client:
        result = await client.query("""
            SELECT count() as issues_count
            FROM (
                SELECT nmid, sum(orders_delta) AS delta_sum,
                       max(total_orders) - min(total_orders) AS total_diff
                FROM default_db.wb_common_stat_incremental
                WHERE timestamp > now() - INTERVAL 1 DAY
                GROUP BY nmid
                HAVING abs(delta_sum - total_diff) > 1
            )
        """)
        
        issues = result.first_item["issues_count"] if result.first_item else 0
        
        if issues > 0:
            logger.warning(f"⚠️ Обнаружено {issues} расхождений в инкрементальной статистике")
        
        return {"issues_count": issues, "status": "ok" if issues == 0 else "warning"}
```

Вызывать из мониторинга 1 раз в день.

---

## Идея для будущего: Инкрементальный учет позиций (wbitemposition)

**Текущее состояние:**
- Таблица `wbitemposition` уже использует `timestamp DateTime`
- Данные записываются с ReplacingMergeTree(version)

**Потенциал:**
Создать инкрементальную таблицу для отслеживания **изменений позиций**:

```sql
CREATE TABLE wbitemposition_incremental (
    nmid UInt64,
    text String,
    timestamp DateTime,
    date Date,
    promo_position_delta Int32,      -- Изменение промо позиции
    base_position_delta Int32,        -- Изменение базовой позиции
    cpm_delta Float64,                -- Изменение CPM
    previous_promo_position UInt32,   -- Предыдущая позиция
    current_promo_position UInt32,    -- Текущая позиция
    version UInt32
) ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(date)
ORDER BY (nmid, text, timestamp);
```

**Применение:**
- Отслеживать скорость изменения позиций (растет/падает за час)
- Детектировать аномалии (резкое падение = нужно увеличить ставку)
- Коррелировать изменения позиций с продажами в реальном времени


