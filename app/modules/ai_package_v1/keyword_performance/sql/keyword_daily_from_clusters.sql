-- ============================================================================
-- keyword_daily_from_clusters.sql
-- ============================================================================
-- Назначение: row-coherent daily snapshot из clusters_adv_stats (argMax forbidden).
-- Таблица(и): default_db.clusters_adv_stats
-- Параметры: adv_ids, first_available, package_cutoff_date, package_cutoff_instant
-- Вызывается: ChKeywordDailyReader.fetch_rows
-- ============================================================================
WITH latest_ts AS (
    SELECT
        adv_id,
        nmid,
        norm_query,
        date,
        max(timestamp) AS last_snapshot_ts
    FROM default_db.clusters_adv_stats
    WHERE adv_id IN {adv_ids:Array(Int32)}
      AND date >= {first_available:Date}
      AND date <= {package_cutoff_date:Date}
      AND timestamp <= {package_cutoff_instant:DateTime}
    GROUP BY adv_id, nmid, norm_query, date
),
rows_at_latest AS (
    SELECT
        s.adv_id,
        s.nmid,
        s.norm_query,
        s.date,
        lt.last_snapshot_ts,
        s.views,
        s.clicks,
        s.add_to_cart,
        s.orders,
        s.spend,
        s.cpm,
        s.cpc,
        s.avr_pos,
        s.ctr
    FROM default_db.clusters_adv_stats AS s
    INNER JOIN latest_ts AS lt
        ON s.adv_id = lt.adv_id
       AND s.nmid = lt.nmid
       AND s.norm_query = lt.norm_query
       AND s.date = lt.date
       AND s.timestamp = lt.last_snapshot_ts
    WHERE s.timestamp <= {package_cutoff_instant:DateTime}
)
SELECT
    adv_id,
    nmid,
    norm_query,
    date,
    last_snapshot_ts,
    uniqExact(
        (views, clicks, add_to_cart, orders, spend, cpm, cpc, avr_pos, ctr)
    ) AS snapshot_variants_at_max_ts,
    any(
        (views, clicks, add_to_cart, orders, spend, cpm, cpc, avr_pos, ctr)
    ) AS snapshot_tuple
FROM rows_at_latest
GROUP BY adv_id, nmid, norm_query, date, last_snapshot_ts
ORDER BY adv_id, nmid, norm_query, date
