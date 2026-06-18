# Минимальные ставки (min_bids) - WB API

## Что это

Функциональность получения минимальных ставок CPM для товаров в рекламных кампаниях через WB Advert API.

## Архитектура

```
WBShopDataManager._set_min_bids()
  [Semaphore(4) для контроля параллелизма]
  ↓
WBDataManager.set_min_bids()
  ↓
PromotionManager.get_min_bids_for_complex_adv()
  [@retry с ротацией токенов, rate-limiting]
  ↓
GetBidsMin.get_bids_min_for_one_placement_type()
  ↓
WB API: POST /adv/v0/bids/min
```

## Ключевые компоненты

- **Rate limiting:** Скользящее окно, 5 req/60s
- **Retry:** До 10 попыток с экспоненциальной задержкой
- **Token rotation:** Автоматическое переключение при 401/403
- **Parallelism control:** Semaphore(4) для ограничения нагрузки
- **Type safety:** Нормализация int для nmid

## Конфигурация

### ENV переменные

```bash
# Production URLs
PROMOTION_BASE_URL=https://advert-api.wildberries.ru
PROMOTION_SANDBOX_URL=https://sandbox-advert-api.wildberries.ru
PROMOTION_TEST_MODE=false  # true для sandbox

# Параллелизм
SHOP_RUNNER_MAX_CONCURRENT_MIN_BIDS_REQUESTS=4

# Retry настройки (опционально, хардкод по умолчанию)
MIN_BIDS_MAX_ATTEMPTS=10
MIN_BIDS_RATE_LIMIT=5  # запросов
MIN_BIDS_RATE_INTERVAL=60  # секунд

# Fallback CPM (руб.) при cache miss на расчётах/UI — не при WB refresh/backfill
MIN_BID_AUTO_DEFAULT=100    # auto/полки; пустой env → 100
MIN_BID_SEARCH_DEFAULT=300    # search/аукцион; пустой env → 300
```

## Fallback при cache miss (расчёты / UI)

Если в Redis нет min_bid для nmid, на **hot path** (cluster bids, emergency при stale stats,
cooldown, UI) подставляется env или встроенный default:

| Env | Встроенный default | Размещение |
|-----|-------------------|------------|
| ``MIN_BID_AUTO_DEFAULT`` | 100 руб. | авто / полки |
| ``MIN_BID_SEARCH_DEFAULT`` | 300 руб. | поиск / аукцион |

Пустая строка в env трактуется как «не задано» → встроенный default.

**Не** подставляется: ``read_min_bids_cache_only``, backfill miss-detection
(``WBManager.get_min_bids(..., apply_defaults=False)``), запись в Redis после WB API.

Реализация: ``app/core/mp/wb/min_bid_defaults.py``, свойства в ``settings_master.py``.

## Redis v2: cache-only чтение (shop-runner / warmup)

После записи через ``MinBidsCacheManager`` consumers читают только Redis:

- ``WBManager.read_min_bids_cache_only`` / ``get_min_bids_cache_only`` — без WB API на hot path.
- **Cache miss** — ``logger.warning`` с подстрокой ``min_bids cache miss`` (ожидаемо до
  ``CoroutinesManager.preload_min_bids_cache_miss`` или прогрева ``snapshot_data_updater``).
  **Не** путать с ERROR ``refresh_min_bids_cache_miss`` (сбой WB refresh).
- Догрузка: ``preload_min_bids_cache_miss`` в ``service_manager/manager.py``.
- Ops-алерты: фильтр WARNING + ``min_bids cache miss``, не ERROR по этой строке.

Подробнее: ``docks/snapshot_data_updater.md`` (раздел «Диагностика»), ``env.sample`` (``SNAPSHOT_MIN_BIDS_*``).

## Troubleshooting

### Проблема: "Rate limit exceeded"

**Симптомы:** Логи показывают много 429 ответов

**Решение:**
1. Увеличить `SHOP_RUNNER_MAX_CONCURRENT_MIN_BIDS_REQUESTS` → 2-3
2. Проверить что rate-limiting работает (логи "Rate limit: sleep")

### Проблема: "No tokens available"

**Симптомы:** `RuntimeError: No tokens for shop_id=...`

**Решение:**
1. Проверить токены в БД для shop_id
2. Проверить что токены валидны (не истекли)
3. Проверить WBCabinetAccess.tokens не пуст

### Проблема: "All advs have empty nmids"

**Симптомы:** Warning логи, min_bids не устанавливаются

**Решение:**
1. Проверить AdvSetting.nmids в БД
2. Убедиться что РК корректно создана

## Smoke test

```bash
python scripts/smoke_min_bids.py
```

## Contacts

Вопросы → #wb-api-team  
Alerts → on-call rotation

