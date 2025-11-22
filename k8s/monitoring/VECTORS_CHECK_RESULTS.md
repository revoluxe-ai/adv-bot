# 🔍 Результаты проверки векторов

## 📋 Дата проверки
2025-11-18

## ✅ Что проверено

### 1. Инфраструктура
- ✅ **predict-ctr-service** - работает (Pod Running)
- ✅ **predict-ctr-updater** - работает
- ✅ **run-shop-update-worker** - работает (4 реплики)
- ✅ **update-keywords-vectors-in-redis-from-neo4j** - работает (записывает векторы)

### 2. Логи predict-ctr-updater
- ⚠️ **Обнаружены сообщения "Нет item_features"** для других кампаний
- Это указывает на проблему с отсутствием векторов товаров в Redis

## 🔴 Проблема

### Код в `app/modules/wb_adv_updater/ML.py:185-187`:
```python
if not avg_item_features:
    logger.debug("Нет item_features: %s", adv.name)
    continue
```

**Это означает:**
- `get_nmid_to_item_features(nmids)` возвращает пустой словарь
- Векторы товаров отсутствуют в Redis для этих nmids
- Кампания пропускается без прогноза CTR

## 🔍 Что нужно проверить для кампании 30554463

### Шаг 1: Получить nmids кампании
```sql
SELECT nmids 
FROM adv_setting 
WHERE adv_id = 30554463;
```

### Шаг 2: Проверить векторы товаров в Redis
Нужно проверить наличие ключей `item_vector:{nmid}` для каждого nmid кампании.

**Проблема:** Не удалось найти Redis pod напрямую. Нужно использовать другой способ доступа к Redis.

### Шаг 3: Проверить векторы товаров в Neo4j
```cypher
MATCH (item:Item)
WHERE item.nmid IN [nmid1, nmid2, ...] // заменить на реальные nmids
RETURN item.nmid, 
       CASE WHEN item.fastrp IS NOT NULL THEN 'HAS_VECTOR' ELSE 'NO_VECTOR' END as status
```

### Шаг 4: Проверить процесс обновления векторов
- Процесс `update-keywords-vectors-in-redis-from-neo4j` работает
- Но нужно проверить процесс обновления **item vectors** (не keyword vectors)

## 🛠️ Решение

### Если векторов нет в Redis:

1. **Найти процесс обновления item vectors:**
   - Должен быть процесс который вызывает `update_items_vectors_in_redis()`
   - Проверить логи `adv-bot-updater` или аналогичного процесса

2. **Перезапустить процесс обновления:**
   ```powershell
   kubectl rollout restart deployment/adv-bot-updater -n prod-adv-bot
   ```

3. **Проверить что процесс загружает векторы:**
   ```powershell
   kubectl logs -n prod-adv-bot deployment/adv-bot-updater --tail=200 | Select-String -Pattern "update.*vector|item.*vector" -CaseSensitive:$false
   ```

### Если векторов нет в Neo4j:

1. **Проверить процесс генерации векторов:**
   - Должен быть процесс который создает `Item.fastrp` в Neo4j
   - Проверить логи graph_vector_updater или аналогичного процесса

2. **Запустить генерацию векторов:**
   - Зависит от архитектуры системы
   - Может потребоваться запуск ML pipeline

## 📊 Текущий статус

- ❌ **Не удалось проверить Redis напрямую** - нужен доступ к Redis pod
- ⚠️ **Логи показывают проблему** - есть кампании без item_features
- ✅ **Процесс обновления keyword vectors работает**
- ❓ **Нужно проверить процесс обновления item vectors**

## 🎯 Следующие шаги

1. **Получить nmids кампании 30554463 из БД**
2. **Найти способ доступа к Redis** (через другой pod или напрямую)
3. **Проверить наличие item_vector в Redis для nmids кампании**
4. **Проверить наличие Item.fastrp в Neo4j**
5. **Проверить процесс обновления item vectors**

---

**Статус:** Требуется доступ к Redis и БД для полной проверки





