WITH
    ------------------------------------------------------------------
    -- 1. Базовые данные из clusters_adv_stats по nmid
    --    Ограничиваем историю по дате, чтобы не взрывать память
    ------------------------------------------------------------------
    data AS (
        SELECT
            norm_query AS text,
            avr_pos    AS avr_position,
            views      AS total_views,
            clicks,
            add_to_cart,
            orders,
            cpm,
            cpc,
            date,
            timestamp
        FROM default_db.clusters_adv_stats
        WHERE nmid = {nmid: UInt64}
    ),

    last_records AS (
        SELECT
            text,
            max(timestamp) AS last_ts,
            argMax(cpm, timestamp) AS last_cpm
        FROM data
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- Базовая агрегация (по дням, с argMax)
    ------------------------------------------------------------------
    daily_last AS (
        SELECT
            text,
            date,
            argMax(total_views, timestamp)  AS views,
            argMax(clicks,      timestamp)  AS clicks,
            argMax(add_to_cart, timestamp)  AS add_to_cart,
            argMax(orders,      timestamp)  AS orders,
            argMax(cpm,         timestamp)  AS cpm,
            argMax(cpc,         timestamp)  AS cpc
        FROM data
        GROUP BY text, date
    ),

    all_time_agg AS (
        SELECT
            text,
            sum(views)  AS views_all_time,
            sum(orders) AS orders_all_time
        FROM daily_last
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- 2. Блок расчёта реальной позиции
    ------------------------------------------------------------------
    day_for_real_position AS (
        SELECT
            text,
            date,
            count(*)         AS versions_count,
            min(total_views) AS views_min,
            max(total_views) AS views_max
        FROM data
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
        FROM data d
        INNER JOIN real_position_valid_day r
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
                pos1, abs(
                (pos1 * views1 - pos2 * views2) / (views1 - views2))
            ) AS pos_real
        FROM pos_real_calc
    ),

    last_avg_position AS (
        SELECT
            text,
            argMax(avr_position, timestamp) AS last_avg_pos
        FROM data
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- 3. УПРОЩЁННЫЙ блок корзина → заказ (для контракта)
    ------------------------------------------------------------------
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

    cart_conv_key_effective AS (
        SELECT
            d.text,
            sum(d.add_to_cart) AS add_to_cart_14d,
            sum(d.orders)      AS orders_14d,
            if(
                sum(d.add_to_cart) > 0,
                sum(d.orders) / sum(d.add_to_cart),
                cb.cart_to_order_conv
            ) AS cart_to_order_conv_effective
        FROM daily_last d
        LEFT JOIN cart_conv_base cb ON 1
        WHERE d.date >= today() - 14
        GROUP BY
            d.text,
            cb.cart_to_order_conv
    ),

    ------------------------------------------------------------------
    -- 4. Информационная агрегатная статистика за 7 дней
    ------------------------------------------------------------------
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

    last_cpc AS (
        SELECT
            text,
            argMax(cpc, timestamp) AS cpc_last
        FROM data
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- 5. Байесовские приоры по кампании
    ------------------------------------------------------------------
    campaign_7d AS (
        SELECT
            sum(views)       AS views_total,
            sum(clicks)      AS clicks_total,
            sum(add_to_cart) AS carts_total,
            sum(orders) AS orders_total
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
        -- показы → клики (7 дней)
        c7.views_total  / (c7.clicks_total + 1)  AS prior_views,

        -- клики → корзины (7 дней)
        c7.clicks_total / (c7.carts_total  + 1)  AS prior_clicks,

        -- корзины → заказы (14 дней)
        c14.carts_total / (c14.orders_total + 1) AS prior_carts
    FROM campaign_7d  AS c7
    CROSS JOIN campaign_14d AS c14
),

    ------------------------------------------------------------------
    -- 6. Окно для CTR (отдельный поток на daily_last)
    ------------------------------------------------------------------
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

    ------------------------------------------------------------------
    -- 7. 7-дневная конверсия клики → корзины
    ------------------------------------------------------------------
    cart_7d AS (
        SELECT
            text,
            sum(clicks)      AS clicks7,
            sum(add_to_cart) AS carts7
        FROM daily_last
        WHERE date >= today() - 7
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- 8. 14-дневная конверсия корзины → заказы
    ------------------------------------------------------------------
    order_14d AS (
        SELECT
            text,
            sum(add_to_cart) AS carts14,
            sum(orders)      AS orders14
        FROM daily_last
        WHERE date >= today() - 14
        GROUP BY text
    ),

    ------------------------------------------------------------------
    -- 9. Байесовский расчёт по воронке
    ------------------------------------------------------------------
    baes AS (
        SELECT
            t.text AS text,
            (c.ctr_clicks + 1) / (c.ctr_views - c.ctr_clicks + p.prior_views) AS ctr_eff,
            (c7.carts7 + 1) / (c7.clicks7 - c7.carts7 + p.prior_clicks)  AS cart_eff,
             (o14.orders14 + 1) / (o14.carts14 - o14.orders14 + p.prior_carts) AS order_eff
        FROM agg_stats AS t
        LEFT JOIN ctr_cut   AS c
            ON c.text = t.text
        LEFT JOIN cart_7d   AS c7
            ON c7.text = t.text
        LEFT JOIN order_14d AS o14
            ON o14.text = t.text
        CROSS JOIN priors   AS p
    )
----------------------------------------------------------------------
-- 10. Финал
----------------------------------------------------------------------
SELECT
    lap.text AS norm_query,
    ifNull(fpr.pos_real, lap.last_avg_pos) AS position,

    -- базовые метрики (за 7 дней)
    ifNull(agg.views_sum,       0)   AS views,
    ifNull(agg.clicks_sum,      0)   AS clicks,
    ifNull(agg.add_to_cart_sum, 0)   AS add_to_cart,
    ifNull(agg.orders_sum,      0)   AS orders,
    ifNull(agg.spend_sum,       0.0) AS spend,

    cb.cart_to_order_conv       AS base_cart_to_order_conv,

    -- эффективная конверсия корзина → заказ (14 дней)
    ifNull(cke.cart_to_order_conv_effective, cb.cart_to_order_conv)
        AS cart_to_order_conv_effective,

    -- прогноз заказов из корзин
    greatest(
        ifNull(agg.add_to_cart_sum, 0) - ifNull(agg.orders_sum, 0),
        0
    ) * ifNull(cke.cart_to_order_conv_effective, cb.cart_to_order_conv)
      AS expected_orders_from_cart,

    -- общий прогноз заказов
    (
        ifNull(agg.orders_sum, 0)
        + greatest(
            ifNull(agg.add_to_cart_sum, 0) - ifNull(agg.orders_sum, 0),
            0
        ) * ifNull(cke.cart_to_order_conv_effective, cb.cart_to_order_conv)
    ) AS expected_orders,

    -- заказы на 1000 показов
    CASE
        WHEN ifNull(agg.views_sum, 0) > 0 THEN
            expected_orders * 1000.0 / ifNull(agg.views_sum, 0)
        ELSE 0.0
    END AS expected_orders_per_1000,

    -- обычный CTR
    (ifNull(agg.clicks_sum, 0) / nullIf(ifNull(agg.views_sum, 0), 0)) AS ctr,

    -- итоговый рейтинг: байесовская цепочка конверсий
    b.ctr_eff * if(b.cart_eff = 0, 1, b.cart_eff)
        * if(b.order_eff = 0, 1, b.order_eff)  AS final_rating,

    -- стат. поля
    ifNull(ata.views_all_time, 0)      AS views_all_time,
    ifNull(ata.orders_all_time, 0)     AS orders_all_time,
    ifNull(lr.last_ts, toDateTime(0))  AS timestamp,
    ifNull(lc.cpc_last, 0.0)           AS cpc,
    ifNull(lr.last_cpm, 0.0)           AS cpm

FROM agg_stats AS agg
LEFT JOIN baes             AS b   ON b.text   = agg.text
LEFT JOIN last_avg_position AS lap ON lap.text = agg.text
LEFT JOIN final_pos_real    AS fpr ON fpr.text = agg.text
LEFT JOIN all_time_agg      AS ata ON ata.text = agg.text
LEFT JOIN last_records      AS lr  ON lr.text  = agg.text
LEFT JOIN last_cpc          AS lc  ON lc.text  = agg.text
LEFT JOIN cart_conv_key_effective AS cke ON cke.text = agg.text
CROSS JOIN cart_conv_base   AS cb
ORDER BY final_rating DESC