SELECT
    COALESCE(SUM(latest_spend), 0.0) AS total_spend
FROM (
    SELECT
        adv_id,
        date,
        argMax(spend, version) AS latest_spend
    FROM default_db.full_adv_wb_stat
    WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
      AND adv_id IN %(adv_ids)s
    GROUP BY adv_id, date
)
