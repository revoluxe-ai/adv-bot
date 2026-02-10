WITH
/* ================================================================
   0) DAILY_LAST — БЕЗ FINAL, через argMaxMerge
   ================================================================ */
daily_last AS (
    SELECT
        text,
        date,

        sum(views0)       AS views,
        sum(clicks0)      AS clicks,
        sum(add_to_cart0) AS add_to_cart,
        sum(orders0)      AS orders,

        /* spend по CPM */
        sum(cpm0 * views0) / 1000.0 AS spend,

        /* CPM weighted by views */
        if(sum(views0) > 0, sum(cpm0 * views0) / sum(views0), 0.0) AS cpm
    FROM
    (
        SELECT
            norm_query AS text,
            date,

            argMaxMerge(views_state)  AS views0,
            argMaxMerge(clicks_state) AS clicks0,
            argMaxMerge(carts_state)  AS add_to_cart0,
            argMaxMerge(orders_state) AS orders0,
            argMaxMerge(cpm_state)    AS cpm0

        FROM default_db.mv_clusters_daily_agg
        WHERE nmid IN {nmids:Array(UInt64)}
        GROUP BY
            norm_query,
            date,
            nmid
    )
    GROUP BY
        text,
        date
),

/* ================================================================
   2) ALL TIME
   ================================================================ */
all_time_agg AS (
    SELECT
        text,
        sum(views)  AS views_all_time,
        sum(orders) AS orders_all_time
    FROM daily_last
    GROUP BY text
),

/* ================================================================
   3) LAST STATE — как было (берётся из last_state MV)
   ================================================================ */
last_state AS (
    SELECT
        text,
        argMaxMerge(last_avg_pos_state) AS last_avg_pos,
        argMaxMerge(last_cpm_state)     AS last_cpm,
        maxMerge(last_ts_state)         AS last_ts
    FROM default_db.mv_clusters_last_state
    WHERE nmid IN {nmids:Array(UInt64)}
    GROUP BY text
),

/* ================================================================
   6) 7-DAY AGG — spend_sum = sum(spend)
   ================================================================ */
agg_stats AS (
    SELECT
        text,
        sum(views)       AS views_sum,
        sum(clicks)      AS clicks_sum,
        sum(add_to_cart) AS add_to_cart_sum,
        sum(orders)      AS orders_sum,
        sum(spend)       AS spend_sum
    FROM daily_last
    WHERE date >= today() - 7
    GROUP BY text
),

/* ================================================================
   4) REAL POSITION — оставляем как было (raw MergeTree)
   ================================================================ */
day_for_real_position AS (
    SELECT
        norm_query AS text,
        date,
        count()     AS versions_count,
        min(views)  AS views_min,
        max(views)  AS views_max
    FROM default_db.clusters_adv_stats
    WHERE nmid IN {nmids:Array(UInt64)}
      AND norm_query IN (SELECT text FROM agg_stats)
    GROUP BY text, date
    HAVING versions_count >= 2
       AND views_min != views_max
),
real_position_valid_day AS (
    SELECT
        text,
        date
    FROM day_for_real_position
    QUALIFY row_number() OVER (
        PARTITION BY text
        ORDER BY date DESC
    ) = 1
),
versions_for_real_pos AS (
    SELECT
        text,
        date,
        arraySlice(arrayMap(x -> x.2, arr), 1, 2) AS pos_arr,
        arraySlice(arrayMap(x -> x.3, arr), 1, 2) AS views_arr
    FROM
    (
        SELECT
            norm_query AS text,
            date,
            arrayReverseSort(groupArray((timestamp, avr_pos, views))) AS arr
        FROM default_db.clusters_adv_stats
        WHERE nmid IN {nmids:Array(UInt64)}
          AND (norm_query, date) IN (SELECT text, date FROM real_position_valid_day)
        GROUP BY
            text, date
    )
),
final_pos_real AS (
    SELECT
        text,
        if(
            arrayElement(views_arr, 1) = arrayElement(views_arr, 2),
            arrayElement(pos_arr, 1),
            abs(
                (
                    arrayElement(pos_arr, 1) * arrayElement(views_arr, 1)
                  - arrayElement(pos_arr, 2) * arrayElement(views_arr, 2)
                )
                / nullIf(arrayElement(views_arr, 1) - arrayElement(views_arr, 2), 0)
            )
        ) AS pos_real
    FROM versions_for_real_pos
    WHERE length(pos_arr) >= 2 AND length(views_arr) >= 2
),

/* ================================================================
   5) CART → ORDER base (14d)
   ================================================================ */
cart_conv_base AS (
    SELECT
        sum(add_to_cart) AS add_to_cart_sum,
        sum(orders)      AS orders_sum,
        if(
            sum(add_to_cart) > 0,
            sum(orders) / nullIf(sum(add_to_cart), 0),
            0.0
        ) AS cart_to_order_conv
    FROM daily_last
    WHERE date >= today() - 14
),

/* ================================================================
   7) PRIORS
   ================================================================ */
campaign_7d AS (
    SELECT
        sum(views)       AS views_total,
        sum(clicks)      AS clicks_total,
        sum(add_to_cart) AS carts_total,
        sum(orders)      AS orders_total
    FROM daily_last
    WHERE date >= today() - 7
),
campaign_14d AS (
    SELECT
        sum(add_to_cart) AS carts_total,
        sum(orders)      AS orders_total
    FROM daily_last
    WHERE date >= today() - 14
),
priors AS (
    SELECT
        c7.views_total  / (c7.clicks_total + 1)  AS prior_views,
        c7.clicks_total / (c7.carts_total  + 1)  AS prior_clicks,
        c14.carts_total / (c14.orders_total + 1) AS prior_carts
    FROM campaign_7d AS c7
    CROSS JOIN campaign_14d AS c14
),

/* ================================================================
   8) CTR — НОВОЕ: ПОСЛЕДНИЕ 500 ПОКАЗОВ из L2 ticks
   ------------------------------------------------
   Берём тики показов/кликов по времени назад.
   running_views = накопленные показы от "сейчас" в прошлое.
   Режем строго по running_views <= 500.
   ================================================================ */
ctr_ticks AS (
    SELECT
        norm_query AS text,
        ts,
        d_views,
        d_clicks,
        sum(d_views) OVER (
            PARTITION BY norm_query
            ORDER BY ts DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_views
    FROM default_db.adv_events_ticks
    WHERE nmid IN {nmids:Array(UInt64)}
      AND d_views > 0
),
ctr_cut AS (
    SELECT
        text,
        sum(d_views)  AS ctr_views,
        sum(d_clicks) AS ctr_clicks
    FROM ctr_ticks
    WHERE running_views <= 500
    GROUP BY text
),

/* ================================================================
   7d/14d разрезы по daily_last — как было
   ================================================================ */
cart_7d AS (
    SELECT
        text,
        sum(clicks)      AS clicks7,
        sum(add_to_cart) AS carts7
    FROM daily_last
    WHERE date >= today() - 7
    GROUP BY text
),
order_14d AS (
    SELECT
        text,
        sum(add_to_cart) AS carts14,
        sum(orders)      AS orders14
    FROM daily_last
    WHERE date >= today() - 14
    GROUP BY text
),

/* ================================================================
   9) BAES — без изменений, только ctr_cut теперь из ticks
   ================================================================ */
baes AS (
    SELECT
        t.text AS text,

        (ifNull(c.ctr_clicks, 0) + 1)
        / greatest(
            ifNull(c.ctr_views, 0) - ifNull(c.ctr_clicks, 0) + greatest(p.prior_views, 1),
            1e-9
        ) AS ctr_eff,

        (ifNull(c7.carts7, 0) + 1)
        / greatest(
            ifNull(c7.clicks7, 0) - ifNull(c7.carts7, 0) + greatest(p.prior_clicks, 1),
            1e-9
        ) AS cart_eff,

        (ifNull(o14.orders14, 0) + 1)
        / greatest(
            ifNull(o14.carts14, 0) - ifNull(o14.orders14, 0) + greatest(p.prior_carts, 1),
            1e-9
        ) AS order_eff
    FROM agg_stats AS t
    LEFT JOIN ctr_cut    AS c   ON c.text  = t.text
    LEFT JOIN cart_7d    AS c7  ON c7.text = t.text
    LEFT JOIN order_14d  AS o14 ON o14.text = t.text
    CROSS JOIN priors    AS p
)

/* ================================================================
   10) FINAL
   ================================================================ */
SELECT
    agg.text AS norm_query,
    ifNull(fpr.pos_real, ls.last_avg_pos) AS position,
    ifNull(agg.views_sum, 0)       AS views,
    ifNull(agg.clicks_sum, 0)      AS clicks,
    ifNull(agg.add_to_cart_sum, 0) AS add_to_cart,
    ifNull(agg.orders_sum, 0)      AS orders,
    ifNull(agg.spend_sum, 0.0)     AS spend,
    cb.cart_to_order_conv AS base_cart_to_order_conv,
    greatest(ifNull(agg.add_to_cart_sum, 0) - ifNull(agg.orders_sum, 0), 0)
        * cb.cart_to_order_conv AS expected_orders_from_cart,
    (
        ifNull(agg.orders_sum, 0)
        + greatest(ifNull(agg.add_to_cart_sum, 0) - ifNull(agg.orders_sum, 0), 0)
            * cb.cart_to_order_conv
    ) AS expected_orders,
    if(
        ifNull(ls.last_cpm, 0) > 0
        AND b.ctr_eff IS NOT NULL,
        (
            b.ctr_eff
            * if(ifNull(b.cart_eff, 0) = 0, 1, b.cart_eff)
            * if(ifNull(b.order_eff, 0) = 0, 1, b.order_eff)
        )
        / ls.last_cpm
        * 100,
        0
    ) AS final_rating,
    if(
        b.ctr_eff IS NOT NULL,
        b.ctr_eff
            * if(ifNull(b.cart_eff, 0) = 0, 1, b.cart_eff)
            * if(ifNull(b.order_eff, 0) = 0, 1, b.order_eff),
        0.0
    ) AS conversion_without_cpm,
    ifNull(ata.views_all_time, 0)     AS views_all_time,
    ifNull(ata.orders_all_time, 0)    AS orders_all_time,
    ifNull(ls.last_ts, toDateTime(0)) AS timestamp,
    ifNull(ls.last_cpm, 0.0)          AS cpm
FROM agg_stats AS agg
LEFT JOIN baes           AS b   ON b.text = agg.text
LEFT JOIN last_state     AS ls  ON ls.text = agg.text
LEFT JOIN final_pos_real AS fpr ON fpr.text = agg.text
LEFT JOIN all_time_agg   AS ata ON ata.text = agg.text
CROSS JOIN cart_conv_base AS cb
ORDER BY final_rating DESC
