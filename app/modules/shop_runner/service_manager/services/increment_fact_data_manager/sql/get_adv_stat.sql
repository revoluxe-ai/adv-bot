WITH latest AS (
    SELECT
        adv_id,
        argMax(views, version) AS views,
        argMax(clicks, version) AS clicks,
        argMax(added_to_cart, version) AS carts,
        argMax(orders, version) AS orders,
        argMax(spend, version) AS spend,
        argMax(sum_price_orders, version) AS sum_price_orders
    FROM default_db.full_adv_wb_stat
    WHERE date = %(report_date)s
      AND adv_id IN %(adv_ids)s
    GROUP BY adv_id
)
SELECT
    COALESCE(SUM(toInt64(views)), 0) AS views_adv_sum,
    COALESCE(SUM(toInt64(clicks)), 0) AS clicks_adv_sum,
    COALESCE(SUM(toInt64(carts)), 0) AS carts_adv_sum,
    COALESCE(SUM(toInt64(orders)), 0) AS orders_adv_sum,
    COALESCE(SUM(toInt64(round(spend))), 0) AS spend_adv_sum_rub,
    COALESCE(SUM(toInt64(round(sum_price_orders))), 0) AS orders_sum_adv_rub
FROM latest
