INSERT INTO default_db.pos_priors_category
WITH
    now() AS calculated_at,
    200 AS alpha_90,
    60  AS alpha_14,
    300 AS max_pos,
    toDate(now()) AS d_today,
    d_today - 89 AS d_from_90d,
    d_today - 13 AS d_from_14d
SELECT
    c.wb_category,
    p.pos_bin,
    (
        ifNull(a.carts_14d, 0)
        + alpha_14 * (
            (ifNull(a.carts_90d, 0) + alpha_90 * g.p_14d)
            / (ifNull(a.views_90d, 0) + alpha_90)
        )
    )
    / (ifNull(a.views_14d, 0) + alpha_14) AS p_14d,
    ifNull(a.views_14d, 0) AS views_14d,
    calculated_at
FROM
(
    /* список категорий, которые вообще существуют в данных */
    SELECT DISTINCT wb_category
    FROM default_db.clusters_adv_deltas_5m
) AS c
CROSS JOIN
(
    /* позиции 1..300 всегда */
    SELECT arrayJoin(range(1, max_pos + 1)) AS pos_bin
) AS p
LEFT JOIN
(
    /* статистика, может отсутствовать -> тогда NULL */
    SELECT
        wb_category,
        pos_bin,
        sumIf(dviews, toDate(ts5) >= d_from_90d AND toDate(ts5) <= d_today) AS views_90d,
        sumIf(dcarts, toDate(ts5) >= d_from_90d AND toDate(ts5) <= d_today) AS carts_90d,
        sumIf(dviews, toDate(ts5) >= d_from_14d AND toDate(ts5) <= d_today) AS views_14d,
        sumIf(dcarts, toDate(ts5) >= d_from_14d AND toDate(ts5) <= d_today) AS carts_14d
    FROM default_db.clusters_adv_deltas_5m
    GROUP BY wb_category, pos_bin
) AS a
    ON a.wb_category = c.wb_category
   AND a.pos_bin = p.pos_bin
INNER JOIN
(
    /* глобальный prior: только последняя версия */
    SELECT
        pos_bin,
        argMax(p_14d, calculated_at) AS p_14d
    FROM default_db.pos_priors_global
    GROUP BY pos_bin
) AS g
    ON g.pos_bin = p.pos_bin
