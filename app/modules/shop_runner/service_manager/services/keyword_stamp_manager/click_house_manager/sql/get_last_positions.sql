WITH
    data AS (
        SELECT
            nmid,
            text,
            timestamp AS ts,
            avr_position,
            total_views,
            lag(total_views) OVER w AS views_old,
            lag(avr_position) OVER w AS avr_old,

            -- последний ts по ключу
            argMax(timestamp, timestamp) OVER (PARTITION BY nmid, text) AS max_ts,

            -- ср. позиция из последней строки
            argMax(avr_position, timestamp) OVER (PARTITION BY nmid, text) AS last_avg_pos,

            -- показы последней строки (то, что тебе нужно вернуть)
            argMax(total_views, timestamp) OVER (PARTITION BY nmid, text) AS last_total_views,
            sum(orders) OVER (PARTITION BY nmid, text) AS total_orders_for_keyword
        FROM default_db.keyword_stamp
        WHERE nmid = {nmid: UInt32}
        WINDOW w AS (
            PARTITION BY nmid, text
            ORDER BY timestamp
        )
    ),
    calc AS (
        SELECT
            *,
            -- реальная позиция блока новых показов
            IF(
                total_views = 0
                OR views_old IS NULL
                OR (total_views - views_old) <= 0,
                NULL,
                (avr_position * total_views - avr_old * views_old)
                    / (total_views - views_old)
            ) AS pos_real
        FROM data
    )
SELECT
    text,
    -- финальная позиция
    IF(
        ts = max_ts AND avr_position = 0 AND total_views = 0,
        0,
        IF(pos_real IS NULL, last_avg_pos, pos_real)
    ) AS real_position,

    -- ВОТ ЭТО: показы из последней строки (всегда самые свежие)
    ts,
    last_total_views AS total_views_last,
    total_orders_for_keyword
FROM calc
QUALIFY row_number() OVER (
    PARTITION BY nmid, text
    ORDER BY
        (ts = max_ts AND avr_position = 0 AND total_views = 0) DESC,
        (pos_real IS NOT NULL) DESC,
        ts DESC
) = 1
ORDER BY text
