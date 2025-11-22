# 🔍 Анализ Pipeline прогнозирования CTR

## 📋 Проблема
Кампания `30554463` для shop_id `76ffadfc-b81e-4ff8-9611-29b7c1c867dc` не получает прогнозы CTR.

## 🔄 Полный Pipeline прогнозирования CTR

### Шаг 1: Инициализация воркера
**Файл:** `app/modules/shop_runner/wb_shop.py`
- `WBShop.run()` запускает все корутины
- `CoroutinesManager.update_predict_ctr()` вызывается каждые **60 секунд** с задержкой **10 секунд**
- Декоратор: `@while_coroutine_decorator(60, 10)`

### Шаг 2: Получение активных кампаний
**Файл:** `app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py`
```python
async def get_active_advs(self) -> list[AdvSetting]:
    shop_id = self.shop_id
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .filter(WBCabinet.shop_id == shop_id, AdvSetting.bot_active)
    )
```

**Условия:**
- ✅ `WBCabinet.shop_id == shop_id` (должен совпадать)
- ✅ `AdvSetting.bot_active == True`

**Если нет активных кампаний:**
- Логируется: `logger.debug("Нет активных кампаний для магазина %s", self.shop_id)`
- Функция возвращается раньше

### Шаг 3: Получение ключевых слов
**Файл:** `app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py`
```python
async def get_calculated_keywords(self, adv: AdvSetting) -> list[CalculatedKeyword]:
    keywords = await get_good_bad_phrases(adv)
    return keywords
```

**Файл:** `app/modules/wb_adv_updater/phrases_processor.py`
- `get_good_bad_phrases()` вызывает `_get_good_bad_phrases_for_min_ctr()`
- Получает статистику из ClickHouse через `get_keywords_statistic_clickhouse()`
- Получает настройки ключевых слов из БД
- Фильтрует и обрабатывает ключевые слова

**Если нет ключевых слов:**
- Логируется: `logger.debug(f"Нет ключевых слов для кампании {adv.adv_id}")`
- Функция возвращается раньше (строка 47-48)

### Шаг 4: Подготовка данных для gRPC
**Файл:** `app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py`
```python
nmids = adv.nmids
phrases = [keyword.text for keyword in keywords]

logger.debug(
    f"Обрабатываем кампанию {adv.adv_id} с {len(nmids)} артикулами и {len(phrases)} ключами"
)
```

**Если есть ключевые слова:**
- Логируется на уровне DEBUG: "Обрабатываем кампанию {adv_id} с {len(nmids)} артикулами и {len(phrases)} ключами"

### Шаг 5: gRPC запрос
```python
grpc_client = await self._get_grpc_client()
predictions = await self._make_grpc_request(grpc_client, nmids, phrases)
```

**Возможные проблемы:**
- `predictions is None` → Логируется WARNING: "Получен None от gRPC сервиса для кампании {adv_id}"
- `predictions == {}` → Логируется WARNING: "Получен пустой словарь прогнозов от gRPC сервиса для кампании {adv_id}"
- gRPC ошибка → Логируется ERROR через `_handle_grpc_error()`

### Шаг 6: Сохранение в Redis
```python
await self._save_predictions_to_redis(adv, predictions)
```

**Логируется на уровне DEBUG:**
- "Сохраняем predictions для ключа '{key} значение: {predict_ctr}"
- "Сохранено {saved_count} прогнозов CTR для кампании {adv_id}"

## 🔍 Точки проверки

### 1. Проверка активности кампании
```sql
SELECT 
    a.adv_id,
    a.bot_active,
    w.shop_id
FROM adv_setting a
JOIN wb_cabinet w ON a.wb_cabinet_id = w.id
WHERE a.adv_id = 30554463;
```

**Ожидаемый результат:**
- `bot_active = true`
- `shop_id = '76ffadfc-b81e-4ff8-9611-29b7c1c867dc'`

### 2. Проверка наличия ключевых слов
```sql
SELECT COUNT(*) 
FROM keyword_setting 
WHERE adv_setting_id = (
    SELECT id FROM adv_setting WHERE adv_id = 30554463
);
```

**Также проверить в ClickHouse:**
- Есть ли статистика по ключевым словам для этой кампании
- За последние 7 дней (по умолчанию)

### 3. Проверка nmids
```sql
SELECT nmids 
FROM adv_setting 
WHERE adv_id = 30554463;
```

**Важно:** `nmids` не должен быть пустым массивом

### 4. Проверка логов

**INFO уровень:**
```bash
kubectl logs -n prod-adv-bot deployment/run-shop-update-worker | grep "Начинаем обновление прогнозов CTR"
```

**DEBUG уровень (может не быть в production):**
```bash
kubectl logs -n prod-adv-bot deployment/run-shop-update-worker | grep "Обрабатываем кампанию\|Нет ключевых слов"
```

**ERROR/WARNING уровень:**
```bash
kubectl logs -n prod-adv-bot deployment/run-shop-update-worker | grep "ERROR\|WARNING" | grep "30554463\|predict_ctr\|gRPC"
```

### 5. Проверка Redis

**Для V1 режима:**
```bash
redis-cli KEYS "predict_ctr:30554463:*"
```

**Для V2 режима:**
Нужно знать nmids кампании:
```bash
redis-cli KEYS "predict_ctr_v2:*:*"
```

## 🎯 Возможные причины проблемы

### Причина 1: Кампания не в списке активных
- ❌ `bot_active = false`
- ❌ `shop_id` не совпадает
- ❌ Кампания не связана с правильным `wb_cabinet`

**Решение:** Проверить БД и исправить

### Причина 2: Нет ключевых слов
- ❌ Нет записей в `keyword_setting` для кампании
- ❌ Нет статистики в ClickHouse за последние 7 дней
- ❌ `get_good_bad_phrases()` возвращает пустой список

**Решение:** 
- Проверить наличие ключевых слов в БД
- Проверить статистику в ClickHouse
- Возможно нужно запустить парсинг ключевых слов

### Причина 3: gRPC сервис не отвечает
- ❌ Сервис недоступен
- ❌ Возвращает None или пустой словарь
- ❌ Ошибка подключения

**Решение:**
- Проверить логи predict-ctr-service
- Проверить переменные окружения PREDICT_CTR_HOST и PREDICT_CTR_PORT
- Проверить сетевую доступность

### Причина 4: Логи на уровне DEBUG
- ❌ Логи не видны в production (уровень DEBUG отключен)
- ❌ Нужно включить DEBUG логирование для этого модуля

**Решение:** Временно включить DEBUG логирование или добавить INFO логи

## 📝 Рекомендации по диагностике

1. **Проверить БД:**
   ```sql
   -- Активность кампании
   SELECT a.*, w.shop_id 
   FROM adv_setting a 
   JOIN wb_cabinet w ON a.wb_cabinet_id = w.id 
   WHERE a.adv_id = 30554463;
   
   -- Ключевые слова
   SELECT COUNT(*) FROM keyword_setting 
   WHERE adv_setting_id = (SELECT id FROM adv_setting WHERE adv_id = 30554463);
   
   -- nmids
   SELECT nmids FROM adv_setting WHERE adv_id = 30554463;
   ```

2. **Включить временное логирование:**
   - Добавить INFO логи в критических точках
   - Или временно включить DEBUG для модуля `predict_ctr_update_manager`

3. **Проверить ClickHouse:**
   - Есть ли статистика по ключевым словам для кампании
   - За какой период есть данные

4. **Проверить Redis:**
   - Есть ли уже сохраненные прогнозы
   - Какой режим используется (V1 или V2)

5. **Мониторинг в реальном времени:**
   ```bash
   kubectl logs -f -n prod-adv-bot deployment/run-shop-update-worker | grep -E "30554463|predict_ctr|Начинаем обновление"
   ```

---

**Дата создания:** 2025-11-18  
**Статус:** Требуется проверка БД и логов





