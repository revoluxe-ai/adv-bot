SELECT
    adv_id,
    argMax(fact_predict_orders, timestamp) AS fact_predict_orders,
    argMax(fact_pay_for_order, timestamp) AS fact_pay_for_order,
    argMax(fact_original_orders, timestamp) AS fact_original_orders,
    argMax(fact_method, timestamp) AS fact_method,
    formatDateTime(max(timestamp), %(plan_fact_ts_format)s, 'Europe/Moscow') AS plan_fact_ch_ts_msk
FROM default_db.plan_fact_stats
WHERE adv_id = %(adv_id)s
GROUP BY adv_id
