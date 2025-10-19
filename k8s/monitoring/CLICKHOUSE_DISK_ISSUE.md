# 🔴 ClickHouse Disk Space Issue - Root Cause & Solution

## Проблема

Диск ClickHouse забивается быстро и заполняется до 50Gb+.

**Причина:** Таблица `full_adv_wb_stat` содержит **дублирующиеся версии** одних и тех же данных.

---

## 📊 Анализ

### Текущая Ситуация

| Параметр | Значение |
|----------|----------|
| Основной PVC | 50Gi (заполнен ~90%) |
| Возраст данных | 245 дней |
| Таблица | `default_db.full_adv_wb_stat` |
| Версионирование | По `version = time.time()` |
| Проблема | Старые версии НЕ удаляются |

### Как Растут Данные

```
День 1: Кампания 1 получает 5 обновлений
  → version 1732000001
  → version 1732000100 (перезапись, но не удаление!)
  → version 1732000200
  → version 1732000300
  → version 1732000400

День 2: То же самое

День 3: То же самое

...

День 245: На каждого из N тысяч кампаний по 5+ версий

ИТОГ: 245 * N * 5 записей вместо N записей! 
```

---

## ✅ Решение

### Вариант 1: Очистить ТОЛЬКО старые версии (РЕКОМЕНДУЕТСЯ)

**Удаляет дубликаты, оставляет последние версии:**

```sql
ALTER TABLE default_db.full_adv_wb_stat DELETE
WHERE version NOT IN (
  SELECT MAX(version) 
  FROM default_db.full_adv_wb_stat
  GROUP BY adv_id, date
);

OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;
```

**Сколько освободится:** ~40Gb (оставит только свежие данные)

### Вариант 2: Удалить старые данные (Если нужны только последние дни)

**Удаляет все данные старше 90 дней:**

```sql
ALTER TABLE default_db.full_adv_wb_stat DELETE 
WHERE date < now() - INTERVAL 90 DAY;

OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;
```

### Вариант 3: Комбинированный (ОПТИМАЛЬНЫЙ)

```sql
-- 1. Удалить дубликаты
ALTER TABLE default_db.full_adv_wb_stat DELETE
WHERE version NOT IN (
  SELECT MAX(version) FROM default_db.full_adv_wb_stat
  GROUP BY adv_id, date
);

-- 2. Удалить старые дни (старше 180 дней)
ALTER TABLE default_db.full_adv_wb_stat DELETE 
WHERE date < now() - INTERVAL 180 DAY;

-- 3. Оптимизировать
OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;
```

---

## 🔧 Как Выполнить

### Способ 1: Через ClickHouse CLI

```bash
# Подключиться к ClickHouse
kubectl exec -it -n default clickhouse-1739529274-shard0-0 -- clickhouse-client

# Выполнить SQL:
ALTER TABLE default_db.full_adv_wb_stat DELETE
WHERE version NOT IN (
  SELECT MAX(version) FROM default_db.full_adv_wb_stat
  GROUP BY adv_id, date
);

OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;
```

### Способ 2: Через скрипт

```bash
kubectl exec -n default clickhouse-1739529274-shard0-0 -- clickhouse-client \
  --query "ALTER TABLE default_db.full_adv_wb_stat DELETE WHERE version NOT IN (SELECT MAX(version) FROM default_db.full_adv_wb_stat GROUP BY adv_id, date);"

kubectl exec -n default clickhouse-1739529274-shard0-0 -- clickhouse-client \
  --query "OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;"
```

---

## ⏱️ Когда Выполнять

- ⏰ **Время:** Ночью (23:00-06:00) во время низкой нагрузки
- 📦 **Продолжительность:** 30-60 минут
- 💾 **Диск:** Нужно чтобы была свободна хотя бы 10Gb

---

## 🛡️ Предотвращение

### Долгосрочное Решение

1. **Добавить политику удаления старых версий**

Изменить код в `full_wb_adv_stat.py`:

```python
async def insert(stats: Iterable[FullAdvStat]) -> None:
    if not stats:
        return

    async with get_clickhouse_client() as client:
        query = _get_insert_query()
        version = str(time.time())
        values = []
        for stat in stats:
            # ... подготовка данных ...
            values.append([...])

        try:
            for row in values:
                await client.query(query, parameters=row)
            
            # ✅ НОВОЕ: Удаляем старые версии после вставки
            # Оставляем только последние 3 версии для каждого adv_id/date
            cleanup_query = """
            ALTER TABLE default_db.full_adv_wb_stat DELETE
            WHERE (adv_id, date) IN (
              SELECT adv_id, date FROM (
                SELECT adv_id, date, version,
                  ROW_NUMBER() OVER (PARTITION BY adv_id, date ORDER BY version DESC) as rn
                FROM default_db.full_adv_wb_stat
              )
              WHERE rn > 3  -- Оставляем только 3 последние версии
            );
            """
            await client.query(cleanup_query)
            
        except Exception:
            logger.error("Ошибка при вставке данных")
```

2. **Добавить TTL для архивирования старых данных**

```sql
ALTER TABLE default_db.full_adv_wb_stat 
MODIFY TTL date + INTERVAL 180 DAY DELETE,
         date + INTERVAL 365 DAY TO DISK 'archive';
```

3. **Мониторить рост таблицы**

Запланировать еженедельную проверку:

```bash
# Cron job
0 2 * * 0 /path/to/check-clickhouse-size.sh
```

---

## 📈 Ожидаемый Результат

**До очистки:**
```
full_adv_wb_stat: 50Gb
```

**После очистки (удаление дубликатов):**
```
full_adv_wb_stat: 3-5Gb  ← Только последние версии
```

**После комбинированной очистки (дубликаты + 180 дней):**
```
full_adv_wb_stat: 1-2Gb  ← Только свежие данные
```

---

## ⚠️ Внимание

- ❌ Не удаляйте без бэкапа
- ❌ Не запускайте во время пиковой нагрузки
- ⏳ Операция может занять 30-60 минут
- 📊 Мониторьте прогресс: `SHOW PROCESSLIST;`

---

## 🆘 Если Что-то Сломалось

```bash
# Проверить статус операции
kubectl exec -n default clickhouse-1739529274-shard0-0 -- clickhouse-client \
  --query "SHOW PROCESSLIST;"

# Посмотреть размер текущей таблицы
kubectl exec -n default clickhouse-1739529274-shard0-0 -- clickhouse-client \
  --query "SELECT table, formatReadableSize(sum(bytes)) as size FROM system.parts WHERE database='default_db' GROUP BY table;"

# Проверить, не хватает ли диска
kubectl get pvc -n default | grep clickhouse
```

---

**Создано:** 2025-10-18  
**Версия:** 1.0  
**Статус:** Рекомендуется выполнить чистку




