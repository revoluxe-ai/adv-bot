WITH
    {nmid:UInt64} AS v_nmid,
    toDate(now()) AS d_today,
    d_today - 13 AS d_from_14d,
    120 AS alpha_key,
    {positions_size:UInt32} AS max_pos,
    (
        SELECT argMax(wb_category, ts5)
        FROM default_db.clusters_adv_deltas_5m
        WHERE nmid = v_nmid
    ) AS v_wb_category
SELECT
    q.norm_query as text,
    pos.pos_bin,
    ifNull(s.views_14d, 0) AS views_14d,
    ifNull(s.carts_14d, 0) AS carts_14d,
    ifNull(c.p_14d, 0) AS p_cat_pos,
    (ifNull(s.carts_14d, 0) + alpha_key * ifNull(c.p_14d, 0))
    /
    (ifNull(s.views_14d, 0) + alpha_key) AS p_key_pos
FROM
(
    SELECT DISTINCT norm_query
    FROM default_db.clusters_adv_deltas_5m
    WHERE nmid = v_nmid
) AS q
CROSS JOIN
(
    SELECT arrayJoin(range(1, max_pos + 1)) AS pos_bin
) AS pos
LEFT JOIN
(
    SELECT
        norm_query,
        pos_bin,
        sumIf(dviews, toDate(ts5) >= d_from_14d AND toDate(ts5) <= d_today) AS views_14d,
        sumIf(dcarts, toDate(ts5) >= d_from_14d AND toDate(ts5) <= d_today) AS carts_14d
    FROM default_db.clusters_adv_deltas_5m
    WHERE nmid = v_nmid
    GROUP BY norm_query, pos_bin
) AS s
    ON s.norm_query = text
   AND s.pos_bin = pos.pos_bin
LEFT JOIN
(
    SELECT
        pos_bin,
        argMax(p_14d, calculated_at) AS p_14d
    FROM default_db.pos_priors_category
    WHERE wb_category = v_wb_category
    GROUP BY pos_bin
) AS c
    ON c.pos_bin = pos.pos_bin
ORDER BY
    text,
    pos.pos_bin
