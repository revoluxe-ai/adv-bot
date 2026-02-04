SELECT
    1
FROM default_db.fact_stat_states
WHERE shop_id = %(shop_id)s
  AND complex_adv_id = %(complex_adv_id)s
  AND bucket_start = %(bucket_start)s
LIMIT 1
