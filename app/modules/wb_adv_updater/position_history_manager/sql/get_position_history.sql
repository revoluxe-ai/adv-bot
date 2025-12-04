WITH
    -- глобальный максимум позиции (для замены нулей)
    max_pos_cte AS (
        SELECT max(avr_pos) AS max_pos
        FROM clusters_adv_stats
    ),

    -- исходные данные с заменой нулей и приведением даты
    prepared AS (
        SELECT
            nmid,
            norm_query AS text,
            -- заменяем нули на max_pos
            CASE WHEN avr_pos = 0 THEN m.max_pos ELSE avr_pos END AS fixed_pos,
            toDate(timestamp) AS date
        FROM clusters_adv_stats AS s
        CROSS JOIN max_pos_cte AS m
        WHERE timestamp >= today() - {last_days: UInt16}
          AND nmid = {nmid: UInt32}
    )

-- средняя позиция по дням и ключам
SELECT
    text,
    date,
    avg(fixed_pos) AS avr_pos
FROM prepared
GROUP BY text, date
ORDER BY text, date
