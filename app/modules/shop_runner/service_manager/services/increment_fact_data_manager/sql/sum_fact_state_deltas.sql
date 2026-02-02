SELECT
    if(sum(carts) = 0, 1, sum(carts))  AS carts,
    if(sum(orders) = 0, 1, sum(orders))  AS orders,
    sum(spend)  AS spend
FROM
(
    SELECT
        argMax(carts_card_sum, version)      AS carts,
        argMax(orders_card_sum, version)     AS orders,
        argMax(spend_adv_sum_rub, version)   AS spend
    FROM default_db.fact_stat_states
    WHERE complex_adv_id = %(complex_adv_id)s
      AND src_ts >= %(from_ts)s
      AND src_ts <= %(to_ts)s
    GROUP BY
        complex_adv_id,
        bucket_start
)
