WITH
    -- Заказы за все дни (исторические + сегодня)
    historical_orders AS (
        SELECT
            text,
            date,
            argMax(orders, version) AS orders_for_day
        FROM default_db.keyword_position_from_api
        WHERE nmid = {nmid: UInt32}
          AND date < today()
        GROUP BY text, date
    ),
    today_orders AS (
        SELECT
            text,
            date,
            argMax(orders, version) AS orders_for_day
        FROM default_db.keyword_stamp
        WHERE nmid = {nmid: UInt32}
          AND date = today()
        GROUP BY text, date
    ),
    all_orders AS (
        SELECT text, orders_for_day FROM historical_orders
        UNION ALL
        SELECT text, orders_for_day FROM today_orders
    ),
    -- Показы ТОЛЬКО за сегодня
    today_views AS (
        SELECT
            text,
            argMax(total_views, version) AS total_views
        FROM default_db.keyword_stamp
        WHERE nmid = {nmid: UInt32}
          AND date = today()
        GROUP BY text
    )
SELECT
    o.text,
    sum(o.orders_for_day) AS total_orders,
    coalesce(v.total_views, 0) AS total_views
FROM all_orders o
LEFT JOIN today_views v ON o.text = v.text
GROUP BY o.text, v.total_views
ORDER BY o.text


