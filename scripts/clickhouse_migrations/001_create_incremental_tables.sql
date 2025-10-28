-- ============================================================================
-- Миграция: Инкрементальные таблицы для продаж в реальном времени
-- Дата: 2025-10-14
-- Описание: Создание таблиц для хранения изменений статистики вместо дневных агрегатов
-- ============================================================================

-- ============================================================================
-- 1. Инкрементальная статистика карточек товаров
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.wb_common_stat_incremental (
    nmid UInt64,                          -- ID товара (как в wb_common_stat)
    timestamp DateTime,                    -- Точное время записи
    date Date,                            -- Дата для партиционирования
    orders_delta Int32,                   -- Изменение заказов с прошлой проверки
    orders_sum_delta Float64,             -- Изменение суммы заказов
    open_card_delta Int32,                -- Изменение открытий карточки
    add_to_cart_delta Int32,              -- Изменение добавлений в корзину
    buy_outs_delta Int32,                 -- Изменение выкупов
    total_orders UInt64,                  -- Накопленное значение заказов (для контроля)
    total_orders_sum Float64,             -- Накопленная сумма заказов
    total_open_card UInt64,               -- Накопленные открытия
    total_add_to_cart UInt64,             -- Накопленные добавления
    total_buy_outs UInt64,                -- Накопленные выкупы
    version UInt64,                       -- Версия записи (timestamp в миллисекундах)
    update_source String DEFAULT 'wb_api',-- Источник обновления
    INDEX incremental_nmid_timestamp_idx (nmid, timestamp) TYPE minmax GRANULARITY 3,
    INDEX incremental_nmid_date_idx (nmid, date) TYPE minmax GRANULARITY 3
) ENGINE = MergeTree()                    -- ✅ Append-only лог событий (НЕ ReplacingMergeTree!)
PARTITION BY toYYYYMM(date)               -- Партиционирование по месяцам
ORDER BY (nmid, timestamp)
SETTINGS index_granularity = 8192;

-- ============================================================================
-- 2. Материализованное представление для часовых агрегатов (общая статистика)
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.wb_common_stat_hourly (
    nmid UInt64,
    hour_start DateTime,
    date Date,
    orders_sum AggregateFunction(sum, Int32),           -- Сумма заказов за час
    orders_sum_rub AggregateFunction(sum, Float64),     -- Сумма в рублях
    open_card_sum AggregateFunction(sum, Int32),        -- Сумма открытий
    add_to_cart_sum AggregateFunction(sum, Int32),      -- Сумма добавлений
    buy_outs_sum AggregateFunction(sum, Int32)          -- Сумма выкупов
) ENGINE = AggregatingMergeTree()         -- Как в advkeyword_daily_mv
PARTITION BY toYYYYMM(date)
ORDER BY (nmid, hour_start)
TTL hour_start + INTERVAL 90 DAY DELETE   -- ✅ Чистим старые агрегаты (дельты остаются!)
SETTINGS index_granularity = 8192;

-- ВАЖНО: POPULATE не используем при первом создании, т.к. таблица пустая
-- ⚙️ Если в ClickHouse уже есть данные в wb_common_stat_incremental,
--    пересоздайте MV с POPULATE для агрегации истории
CREATE MATERIALIZED VIEW IF NOT EXISTS default_db.wb_common_stat_hourly_mv 
TO default_db.wb_common_stat_hourly
AS SELECT
    nmid,
    toStartOfHour(timestamp) as hour_start,
    toDate(timestamp) as date,
    sumState(orders_delta) as orders_sum,
    sumState(orders_sum_delta) as orders_sum_rub,
    sumState(open_card_delta) as open_card_sum,
    sumState(add_to_cart_delta) as add_to_cart_sum,
    sumState(buy_outs_delta) as buy_outs_sum
FROM default_db.wb_common_stat_incremental
GROUP BY nmid, hour_start, date;

-- ============================================================================
-- 3. Инкрементальная статистика рекламных кампаний
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.full_adv_wb_stat_incremental (
    adv_id Int32,                         -- ID рекламы (как в full_adv_wb_stat)
    timestamp DateTime,                    -- Точное время записи
    date Date,                            -- Дата для партиционирования
    orders_delta Int32,                   -- Изменение заказов
    spend_delta Float32,                  -- Изменение расходов (Float32 как в оригинале)
    sum_price_delta Float32,              -- Изменение суммы заказов
    views_delta Int32,                    -- Изменение просмотров
    clicks_delta Int32,                   -- Изменение кликов
    added_to_cart_delta Int32,            -- Изменение добавлений в корзину
    total_orders Int32,                   -- Накопленные заказы (для контроля)
    total_spend Float32,                  -- Накопленные расходы
    total_sum_price Float32,              -- Накопленная сумма заказов
    total_views Int32,                    -- Накопленные просмотры
    total_clicks Int32,                   -- Накопленные клики
    total_added_to_cart Int32,            -- Накопленные добавления
    version Float64,                      -- Версия (Float64 как в full_adv_wb_stat)
    INDEX incremental_adv_timestamp_idx (adv_id, timestamp) TYPE minmax GRANULARITY 3,
    INDEX incremental_adv_date_idx (adv_id, date) TYPE minmax GRANULARITY 3
) ENGINE = MergeTree()                    -- ✅ Append-only лог событий
PARTITION BY toYYYYMM(date)
ORDER BY (adv_id, timestamp)
SETTINGS index_granularity = 8192;

-- ============================================================================
-- 4. Материализованное представление для часовых агрегатов (реклама)
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.full_adv_wb_stat_hourly (
    adv_id Int32,
    hour_start DateTime,
    date Date,
    orders_sum AggregateFunction(sum, Int32),
    spend_sum AggregateFunction(sum, Float32),
    sum_price_sum AggregateFunction(sum, Float32),
    views_sum AggregateFunction(sum, Int32),
    clicks_sum AggregateFunction(sum, Int32),
    added_to_cart_sum AggregateFunction(sum, Int32)
) ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (adv_id, hour_start)
TTL hour_start + INTERVAL 90 DAY DELETE   -- ✅ Чистим старые агрегаты
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS default_db.full_adv_wb_stat_hourly_mv
TO default_db.full_adv_wb_stat_hourly
AS SELECT
    adv_id,
    toStartOfHour(timestamp) as hour_start,
    toDate(timestamp) as date,
    sumState(orders_delta) as orders_sum,
    sumState(spend_delta) as spend_sum,
    sumState(sum_price_delta) as sum_price_sum,
    sumState(views_delta) as views_sum,
    sumState(clicks_delta) as clicks_sum,
    sumState(added_to_cart_delta) as added_to_cart_sum
FROM default_db.full_adv_wb_stat_incremental
GROUP BY adv_id, hour_start, date;

-- ============================================================================
-- ПРИМЕЧАНИЯ
-- ============================================================================

-- Применение миграции:
-- clickhouse-client --query "$(cat 001_create_incremental_tables.sql)"

-- Проверка созданных таблиц:
-- SHOW TABLES LIKE '%incremental%';
-- SHOW TABLES LIKE '%hourly%';

-- Пример запроса заказов за последние 6 часов:
-- SELECT 
--     nmid,
--     sumMerge(orders_sum) as total_orders
-- FROM default_db.wb_common_stat_hourly
-- WHERE hour_start >= now() - INTERVAL 6 HOUR
--   AND nmid = 123456
-- GROUP BY nmid;

-- Пример пересоздания MV с POPULATE (если нужно заполнить историю):
-- DROP VIEW default_db.wb_common_stat_hourly_mv;
-- CREATE MATERIALIZED VIEW default_db.wb_common_stat_hourly_mv
-- TO default_db.wb_common_stat_hourly
-- POPULATE  -- ← Заполнит историю из wb_common_stat_incremental
-- AS SELECT ...;


