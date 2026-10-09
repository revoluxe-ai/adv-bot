-- ============================================================================
-- keyword_position_from_api.sql
-- ============================================================================
-- Назначение: WB keyword position API stream (row-coherent max version ms epoch).
-- Таблица(и): default_db.keyword_position_from_api
-- Параметры: nmids, position_first_available, package_cutoff_date, cutoff_instant_ms
-- Вызывается: ChKeywordPositionReader.fetch_rows
-- Примечание: внешний alias — max_version, не version. Alias version
--   подставляется в uniqExact/any и даёт CH Code 184 ILLEGAL_AGGREGATION.
-- ============================================================================
WITH latest_version AS (
    SELECT
        nmid,
        text,
        date,
        max(version) AS max_version
    FROM default_db.keyword_position_from_api
    WHERE nmid IN {nmids:Array(Int32)}
      AND date >= {position_first_available:Date}
      AND date <= {package_cutoff_date:Date}
      AND version <= {cutoff_instant_ms:UInt64}
    GROUP BY nmid, text, date
),
rows_at_max AS (
    SELECT
        s.nmid,
        s.text,
        s.date,
        s.version,
        s.avr_position,
        s.total_views,
        s.orders
    FROM default_db.keyword_position_from_api AS s
    INNER JOIN latest_version AS lv
        ON s.nmid = lv.nmid
       AND s.text = lv.text
       AND s.date = lv.date
       AND s.version = lv.max_version
    WHERE s.version <= {cutoff_instant_ms:UInt64}
)
SELECT
    nmid,
    text,
    date,
    -- Alias must not be `version`: ClickHouse rewrites that name inside
    -- uniqExact/any and raises Code 184 (max nested in another aggregate).
    max(version) AS max_version,
    uniqExact(
        (avr_position, total_views, orders, version)
    ) AS tuple_variants_at_max_version,
    any(
        (avr_position, total_views, orders, version)
    ) AS position_tuple
FROM rows_at_max
GROUP BY nmid, text, date
ORDER BY nmid, text, date
