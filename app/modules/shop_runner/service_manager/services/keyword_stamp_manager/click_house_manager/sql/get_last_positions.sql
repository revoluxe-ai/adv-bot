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
            max(timestamp) OVER (PARTITION BY nmid, text) AS max_ts,

            -- средняя позиция из последней строки (по max(timestamp))
            argMax(avr_position, timestamp) OVER (PARTITION BY nmid, text) AS last_avg_pos
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
    -- 1) если последняя строка (по времени) и там avr_position = 0 и показов 0 → возвращаем 0
    -- 2) иначе, если pos_real есть → берём её
    -- 3) иначе → берём avr_position из последней строки (last_avg_pos)
    IF(
        ts = max_ts AND avr_position = 0 AND total_views = 0,
        0,
        IF(pos_real IS NULL, last_avg_pos, pos_real)
    ) AS real_position,
    ts
FROM calc
QUALIFY row_number() OVER (
    PARTITION BY nmid, text
    ORDER BY
        -- сначала приоритезируем кейс "последняя строка и она 0/0"
        (ts = max_ts AND avr_position = 0 AND total_views = 0) DESC,
        -- затем строки, где удалось посчитать pos_real
        (pos_real IS NOT NULL) DESC,
        -- внутри по времени (самая свежая)
        ts DESC
) = 1
ORDER BY text
