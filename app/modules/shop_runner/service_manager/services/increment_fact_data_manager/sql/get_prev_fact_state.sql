SELECT
    shop_id,
    complex_adv_id,
    bucket_start,
    views_adv_sum,
    clicks_adv_sum,
    carts_adv_sum,
    orders_adv_sum,
    spend_adv_sum_rub,
    orders_sum_adv_rub,
    open_card_sum,
    carts_card_sum,
    orders_card_sum,
    orders_sum_card_rub,
    buy_outs_sum,
    src_ts,
    version
FROM default_db.fact_stat_states_prev
WHERE shop_id = %(shop_id)s
  AND complex_adv_id = %(complex_adv_id)s
ORDER BY version DESC
LIMIT 1
