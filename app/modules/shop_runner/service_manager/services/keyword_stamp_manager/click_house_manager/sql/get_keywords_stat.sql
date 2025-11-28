WITH
    data AS (SELECT text,
                    avr_position,
                    orders,
                    total_views,
                    date,
                    timestamp,
                    version
FROM default_db.keyword_stamp
WHERE nmid = {nmid: UInt64}
    AND date >= today() - INTERVAL {days: UInt32} DAYS
    ),

    total_sums_today AS (
        SELECT
            text,
            date,
            argMax(orders, version) as orders_sum,
               argMax(total_views, version) as views_sum
        FROM data
          WHERE date = today()
              GROUP BY (text, date)
    ),
     later_sums AS (
              SELECT
                  text,
                  date,
                  argMax(orders, version) as orders_sum,
                  argMax(total_views, version) as views_sum
              FROM default_db.keyword_position_from_api
                  WHERE date < today()
                      AND nmid = {nmid: UInt64}
                      GROUP BY (text, date)
    ),
     union_sum AS (
          SELECT text, orders_sum, views_sum FROM total_sums_today
          UNION ALL
          SELECT text, orders_sum, views_sum FROM later_sums
    ),
     final_sum AS (
           SELECT
               text,
               sum(orders_sum) as orders_sum,
               sum(views_sum) as views_sum
               FROM union_sum
                   GROUP BY (text)
    ),
      day_for_real_position AS (
                       SELECT
                            text,
                            date,
                            count(*) AS versions_count,
                            min(total_views) AS views_min,
                            max(total_views) AS views_max
                        FROM data
                        GROUP BY text, date
                        HAVING versions_count >= 2
                           AND views_min != views_max
    ),
        real_position_valide_day AS (
            SELECT
                text,
                date
                    FROM day_for_real_position
                    QUALIFY row_number() OVER (PARTITION BY text ORDER BY date DESC) = 1
    ), versions_for_real_pos AS (
    SELECT
        d.text,
        d.date,
        d.avr_position,
        d.total_views,
        d.version,
        row_number() OVER (
            PARTITION BY d.text, d.date
            ORDER BY d.version DESC
        ) AS rn
    FROM data d
    INNER JOIN real_position_valide_day r
        ON r.text = d.text
       AND r.date = d.date
), pos_real_calc AS (
    SELECT
        text,
        date,
        maxIf(avr_position, rn = 1) AS pos1,
        maxIf(total_views, rn = 1) AS views1,
        maxIf(avr_position, rn = 2) AS pos2,
        maxIf(total_views, rn = 2) AS views2
    FROM versions_for_real_pos
    GROUP BY text, date
), final_pos_real AS (
    SELECT
        text,
        date,
        if(
            views1 = views2,
            pos1,
            ((pos1 * views1) - (pos2 * views2)) /(views1 - views2)) AS pos_real
            FROM pos_real_calc),

last_ts AS (
    SELECT
        text,
        argMax(timestamp, version) AS last_timestamp
    FROM data
    GROUP BY text
),
last_avg_position AS (
    SELECT
        text,
        argMax(avr_position, version) AS last_avg_pos
    FROM data
    GROUP BY text
)

SELECT
    fs.text,
    coalesce(pr.pos_real, lap.last_avg_pos),
    fs.views_sum AS total_views,
    fs.orders_sum AS total_orders,
    lt.last_timestamp
FROM final_sum fs
LEFT JOIN final_pos_real pr ON pr.text = fs.text
LEFT JOIN last_avg_position lap ON lap.text = fs.text
LEFT JOIN last_ts lt ON lt.text = fs.text
ORDER BY fs.text












