WITH
/* ================================================================
   1) DAILY_LAST — восстанавливаем дневные значения из Aggregating MV
   ================================================================ */
daily_last AS (
    SELECT
        text,
        date,
        argMaxMerge(views_state)        AS views,
        argMaxMerge(clicks_state)       AS clicks,
        argMaxMerge(add_to_cart_state)  AS add_to_cart,
        argMaxMerge(orders_state)       AS orders,
        argMaxMerge(cpm_state)          AS cpm,
        argMaxMerge(cpc_state)          AS cpc,
        maxMerge(ts_state)              AS last_ts_day
    FROM default_db.mv_clusters_daily
    WHERE nmid = {nmid: UInt64}
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
   3) LAST STATE — как в старом контракте (timestamp/cpc/cpm/avg_pos)
   ================================================================ */
last_state AS (
    SELECT
        text,
        argMaxMerge(last_avg_pos_state) AS last_avg_pos,
        argMaxMerge(last_cpc_state)     AS cpc_last,
        argMaxMerge(last_cpm_state)     AS last_cpm,
        maxMerge(last_ts_state)         AS last_ts
    FROM default_db.mv_clusters_last_state
    WHERE nmid = {nmid: UInt64}
    GROUP BY text
),

/* ================================================================
   4) REAL POSITION — оставляем из clusters_adv_stats (как было)
   ================================================================ */
data_pos AS (
    SELECT
        norm_query AS text,
        avr_pos    AS avr_position,
        views      AS total_views,
        date,
        timestamp
    FROM default_db.clusters_adv_stats
    WHERE nmid = {nmid: UInt64}
),

day_for_real_position AS (
    SELECT
        text,
        date,
        count(*)         AS versions_count,
        min(total_views) AS views_min,
        max(total_views) AS views_max
    FROM data_pos
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
        d.text,
        d.date,
        d.avr_position,
        d.total_views,
        d.timestamp,
        row_number() OVER (
            PARTITION BY d.text, d.date
            ORDER BY d.timestamp DESC
        ) AS rn
    FROM data_pos AS d
    INNER JOIN real_position_valid_day AS r
        ON r.text = d.text
       AND r.date = d.date
),

pos_real_calc AS (
    SELECT
        text,
        maxIf(avr_position, rn = 1) AS pos1,
        maxIf(total_views,  rn = 1) AS views1,
        maxIf(avr_position, rn = 2) AS pos2,
        maxIf(total_views,  rn = 2) AS views2
    FROM versions_for_real_pos
    GROUP BY text
),

final_pos_real AS (
    SELECT
        text,
        if(
            views1 = views2,
            pos1,
            abs((pos1 * views1 - pos2 * views2) / (views1 - views2))
        ) AS pos_real
    FROM pos_real_calc
),

/* ================================================================
   5) CART → ORDER (контрактный блок)
   ================================================================ */
cart_conv_base AS (
    SELECT
        sum(add_to_cart) AS add_to_cart_sum,
        sum(orders)      AS orders_sum,
        if(
            sum(add_to_cart) > 0,
            sum(orders) / sum(add_to_cart),
            0.0
        ) AS cart_to_order_conv
    FROM daily_last
    WHERE date >= today() - 14
),

/* ================================================================
   6) 7-DAY AGG (как в исходном: spend = cpm*views/1000 + cpc*clicks)
   ================================================================ */
agg_stats AS (
    SELECT
        text,
        sum(views)       AS views_sum,
        sum(clicks)      AS clicks_sum,
        sum(add_to_cart) AS add_to_cart_sum,
        sum(orders)      AS orders_sum,
        sum((cpm * views) / 1000.0 + (cpc * clicks)) AS spend_sum
    FROM daily_last
    WHERE date >= today() - 7
    GROUP BY text
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
   8) CTR WINDOW (500 views)
   ================================================================ */
ctr_window AS (
    SELECT
        text,
        date,
        views,
        clicks,
        sum(views) OVER (
            PARTITION BY text
            ORDER BY date DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_views
    FROM daily_last
    WHERE date >= today() - 7
),

ctr_cut AS (
    SELECT
        text,
        sum(views)  AS ctr_views,
        sum(clicks) AS ctr_clicks
    FROM ctr_window
    WHERE (running_views - views) < 500
    GROUP BY text
),

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
   9) BAES — ВАЖНО: t.text AS text (чтобы b.text точно существовал)
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
   10) FINAL — контракт 1:1 со старым запросом
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
        * cb.cart_to_order_conv
      AS expected_orders_from_cart,

    (
        ifNull(agg.orders_sum, 0)
        + greatest(ifNull(agg.add_to_cart_sum, 0) - ifNull(agg.orders_sum, 0), 0)
            * cb.cart_to_order_conv
    ) AS expected_orders,

    ifNull(
    (
        b.ctr_eff
        * if(ifNull(b.cart_eff, 0) = 0, 1, b.cart_eff)
        * if(ifNull(b.order_eff, 0) = 0, 1, b.order_eff)
    )
    / nullIf(pfr.price, 0)
    * 100,
    0
) AS final_rating,

    ifNull(ata.views_all_time, 0)      AS views_all_time,
    ifNull(ata.orders_all_time, 0)     AS orders_all_time,
    ifNull(ls.last_ts, toDateTime(0))  AS timestamp,
    ifNull(ls.cpc_last, 0.0)           AS cpc,
    ifNull(ls.last_cpm, 0.0)           AS cpm

FROM agg_stats AS agg
LEFT JOIN baes            AS b   ON b.text = agg.text
LEFT JOIN last_state      AS ls  ON ls.text = agg.text
LEFT JOIN final_pos_real  AS fpr ON fpr.text = agg.text
LEFT JOIN all_time_agg    AS ata ON ata.text = agg.text
CROSS JOIN cart_conv_base AS cb
ORDER BY final_rating DESC
