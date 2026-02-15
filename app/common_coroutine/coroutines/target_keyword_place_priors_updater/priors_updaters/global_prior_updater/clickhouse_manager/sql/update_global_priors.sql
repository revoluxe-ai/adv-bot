INSERT INTO default_db.pos_priors_global
(
    pos_bin,
    views_all, carts_all, p_all,
    views_90d, carts_90d, p_90d,
    views_14d, carts_14d, p_14d,
    p0_used,
    calculated_at
)
WITH
    toFloat64(200) AS alpha_90,
    toFloat64(60)  AS alpha_14
SELECT
    pos_bin,
    views_all,
    carts_all,
    carts_all / nullIf(views_all, 0) AS p_all,
    views_90d,
    carts_90d,
    p_90d,
    views_14d,
    carts_14d,
    -- p_14d: 14 дней, сглаженные prior'ом p_90d
    (toFloat64(carts_14d) + alpha_14 * p_90d)
        / nullIf(toFloat64(views_14d) + alpha_14, 0) AS p_14d,
    p0_used,
    now() AS calculated_at
FROM
(
    SELECT
        pos_bin,
        views_all,
        carts_all,
        views_90d,
        carts_90d,
        views_14d,
        carts_14d,
        -- глобальный prior по 90 дням (один на всю выборку)
        (sum(carts_90d) OVER () / nullIf(sum(views_90d) OVER (), 0)) AS p0_used,
        -- p_90d: 90 дней, сглаженные prior'ом p0_used
        (toFloat64(carts_90d) + alpha_90
            * (sum(carts_90d) OVER () / nullIf(sum(views_90d) OVER (), 0))
        )
            / nullIf(toFloat64(views_90d) + alpha_90, 0) AS p_90d
    FROM
    (
        SELECT
            pos_bin,
            sum(toUInt64(dviews)) AS views_all,
            sum(toUInt64(dcarts)) AS carts_all,
            sumIf(toUInt64(dviews), ts5 >= now() - INTERVAL 90 DAY) AS views_90d,
            sumIf(toUInt64(dcarts), ts5 >= now() - INTERVAL 90 DAY) AS carts_90d,
            sumIf(toUInt64(dviews), ts5 >= now() - INTERVAL 14 DAY) AS views_14d,
            sumIf(toUInt64(dcarts), ts5 >= now() - INTERVAL 14 DAY) AS carts_14d
        FROM default_db.clusters_adv_deltas_5m
        GROUP BY pos_bin
    )
)
