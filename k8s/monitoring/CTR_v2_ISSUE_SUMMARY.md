# 🔴 CTR v2 Issue Summary - Магазин e46468f2-3d7d-43ec-9113-d590e51452ea

## Проблема

CTR v2 **не прогнозируется** для конкретного магазина. Вместо прогнозов видим пропуск кампаний с ошибкой:
```
Нет item_features: <campaign_id>
```

## Корневая Причина

| Уровень | Статус | Описание |
|---------|--------|---------|
| **Neo4j** | ❌ КРИТИЧНО | Item nodes **БЕЗ fastrp vectors** (найдено: 0) |
| **Redis** | ❌ КРИТИЧНО | item_vector ключей **НЕТ** (найдено: 0) |
| **CTR Updater** | ❌ ПРОПУСК | 161 из 777 кампаний (20%) пропущены |

## Процесс, Который Должен Работать

```
Neo4j (Item nodes)
       ↓
       ✅ (должны быть Item с fastrp)
       ↓
DataScience.update_items_vectors_in_redis()
       ↓
Redis (item_vector:*)
       ↓
predict_ctr_updater.get_nmid_to_item_features()
       ↓
✅ CTR Predictions
```

## Что Сломалось

```
Neo4j (Item nodes)
       ↓
       ❌ БЕЗ fastrp (0 nodes)
       ↓
Redis (item_vector:*)
       ↓
       ❌ БЕЗ данных (0 keys)
       ↓
predict_ctr_updater
       ↓
       ❌ avg_item_features пусто
       ↓
       ❌ Кампания пропускается
```

## Диагностика

### Выполненные Проверки

✅ predict-ctr-updater pod - **работает**
✅ predict-ctr-service pod - **работает**  
✅ Явных ошибок в логах - **нет**
✅ Обновление CTR работает - **да**

❌ Item vectors в Neo4j - **0**
❌ Item vectors в Redis - **0**
❌ Процент успешных предсказаний - **~80%**

### Статистика

- Всего обработано кампаний: **777**
- Успешно предсказано: **616** (79%)
- Пропущено (нет item_features): **161** (21%)

## Возможные Причины

1. **Процесс graph_vector_updater не загрузил данные** в Neo4j
2. **DataScience.update_items_vectors_in_redis()** не был вызван при последнем запуске
3. **Отсутствие данных о товарах** в системе для конкретного магазина
4. **Neo4j connection timeout** при попытке загрузить vectors

## Решение

### Шаг 1: Проверка Логов

```bash
kubectl logs -n default <adv-bot-updater-pod> --tail=200 \
  | grep -i 'update_items_vectors\|update_vectors'
```

### Шаг 2: Перезагрузка Pod (Рекомендуется)

```bash
kubectl rollout restart deployment/adv-bot-updater -n default
```

Это заставит процесс `update_vectors_in_redis()` пересчитать и загрузить все item vectors.

### Шаг 3: Проверка Результата

```bash
./ctr-final-diagnosis.sh
```

После перезагрузки (подождать 2-3 минуты) item_vector ключей должны появиться в Redis.

### Шаг 4: Если Проблема Остается

Если Item nodes в Neo4j все еще = 0:

1. Проверьте, загружаются ли данные о товарах:
   ```bash
   kubectl logs -n default <graph-updater-pod> --tail=100
   ```

2. Проверьте таблицу ItemFeature в БД:
   ```bash
   SELECT COUNT(*) FROM item_feature;
   ```

3. Если таблица пустая - нужно запустить полную загрузку данных о товарах

## Команды для Скрытов

| Скрипт | Цель |
|--------|------|
| `./access-monitoring-ui.sh` | Открыть Prometheus, Grafana, AlertManager |
| `./view-logs.sh [component]` | Просмотр логов компонента |
| `./debug-ctr.sh <shop_id>` | Отладка CTR для магазина |
| `./ctr-status.sh` | Общий статус CTR v2 |
| `./ctr-final-diagnosis.sh` | Полная диагностика |
| `./fix-ctr-vectors.sh` | Рекомендации по исправлению |

## Влияние

- **Магазин:** e46468f2-3d7d-43ec-9113-d590e51452ea
- **Состояние:** ⚠️ Частичное (работает, но не все кампании)
- **Приоритет:** 🟠 Средний (работает для ~80% кампаний)

## Дальнейшие Шаги

1. Выполнить перезагрузку adv-bot-updater
2. Подождать 3-5 минут на инициализацию
3. Запустить `./ctr-final-diagnosis.sh` для проверки
4. Если проблема остается - проверить Neo4j и таблицу ItemFeature

---

**Создано:** 2025-10-18  
**Версия:** 1.0  
**Статус:** 🔴 Требуется Исправление

