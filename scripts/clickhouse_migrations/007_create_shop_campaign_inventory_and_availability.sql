-- ============================================================================
-- 007_create_shop_campaign_inventory_and_availability.sql
-- ============================================================================
-- Назначение: DDL inventory и append-only availability для shop-wide RECORD
--   сбора (design §D.1, §D.3, §F.2). Не executor сбора и не Job в scripts/.
--   Durable route epoch — только shop_campaign_inventory.route_version.
--   Redis MAY координировать lock в runtime и MUST NOT быть вторым epoch SoT;
--   эта миграция не создаёт Redis-ключ и не хранит epoch вне inventory.
-- Таблица(и): default_db.shop_campaign_inventory,
--   default_db.shop_campaign_collection_availability
-- Параметры: нет (DDL, без %(param)s)
-- Вызывается: вручную как CH-миграция; контракт проверяет
--   tests/unit/shop_runner/test_shop_campaign_inventory_ddl.py
-- Qualification: openspec/decisions/clickhouse-sql-database-qualification/decision.md
-- Placement: proposed decision
--   openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md
-- Debt: openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md
-- Типы из существующих фактов, не новые product enum:
--   shop_id String — WBShop.shop_id и CH plan_fact_stats / fact_stat_states
--   adv_id Int64 — PG AdvSetting.adv_id BIGINT
--   nm_ids Array(UInt64) — CH nmid UInt64 (wb_common_stat, clusters_adv_stats)
--   version UInt64 — monotonic optimistic concurrency (ReplacingMergeTree),
--     отдельно от route_version
-- Availability identity (shop_id, adv_id, collector_id) — ключ debt §safeguards
--   и upsert-ключ inventory; reason_code / route_version — diagnostic plane.
--   Literal enum reason_code / collector_id не закрыты (design Open Questions):
--   колонки String, без Enum.
-- Существующие fact-таблицы (full_adv_wb_stat, wb_common_stat, clusters_adv_stats)
--   эта миграция не изменяет.
-- ============================================================================

-- ============================================================================
-- default_db.shop_campaign_inventory
-- Upsert одной текущей строки на (shop_id, adv_id).
-- route_version — единственный durable route epoch (не аргумент ENGINE).
-- version — monotonic optimistic concurrency для ReplacingMergeTree.
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.shop_campaign_inventory
(
    shop_id String,
    adv_id Int64,
    nm_ids Array(UInt64),
    wb_status String,
    wb_lifecycle String,
    route String,
    discovered_at DateTime,
    last_seen_at DateTime,
    route_version UInt64,
    version UInt64
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (shop_id, adv_id)
SETTINGS index_granularity = 8192;

-- ============================================================================
-- default_db.shop_campaign_collection_availability
-- Append-only диагностика (НЕ ReplacingMergeTree): ошибка / skip / reconcile
-- не затирает предыдущую строку. route_version копирует сверенный epoch
-- inventory и не заменяет запрет записи fact grain.
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_db.shop_campaign_collection_availability
(
    shop_id String,
    adv_id Int64,
    collector_id String,
    reason_code String,
    route_version UInt64
)
ENGINE = MergeTree()
ORDER BY (shop_id, adv_id, collector_id, route_version, reason_code)
SETTINGS index_granularity = 8192;
