SELECT
    if(sum(orders) = 0, 1, sum(orders)) / if(sum(carts) = 0, 1, sum(carts)) as ratio
FROM
    (
        SELECT if (carts < orders, orders, carts) as carts,
               orders
               FROM
                    (SELECT
                        argMax(add_to_cart, version) as carts,
                        argMax(orders, version) as orders
                    FROM default_db.wb_common_stat
                    WHERE nmid IN %(nmids)s
                      AND date BETWEEN %(from_date)s AND %(to_date)s
                    GROUP BY nmid, date))
