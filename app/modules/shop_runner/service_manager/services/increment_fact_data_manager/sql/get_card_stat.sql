WITH latest AS (
    SELECT
        nmid,
        argMax(open_card, version) AS open_card,
        argMax(add_to_cart, version) AS add_to_cart,
        argMax(orders, version) AS orders,
        argMax(orders_sum, version) AS orders_sum,
        argMax(buy_outs, version) AS buy_outs
    FROM default_db.wb_common_stat
    WHERE date = %(report_date)s
      AND nmid IN %(nmids)s
    GROUP BY nmid
)
SELECT
    COALESCE(SUM(toInt64(open_card)), 0) AS open_card_sum,
    COALESCE(SUM(toInt64(add_to_cart)), 0) AS carts_card_sum,
    COALESCE(SUM(toInt64(orders)), 0) AS orders_card_sum,
    COALESCE(SUM(toInt64(round(orders_sum))), 0) AS orders_sum_card_rub,
    COALESCE(SUM(toInt64(buy_outs)), 0) AS buy_outs_sum
FROM latest
