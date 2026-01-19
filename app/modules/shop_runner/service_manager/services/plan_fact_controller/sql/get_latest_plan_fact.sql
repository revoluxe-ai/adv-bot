SELECT
    adv_id,
    argMax(plan_orders, timestamp) AS plan_orders,
    argMax(plan_target_pay_for_order, timestamp) AS plan_target_pay_for_order,
    argMax(plan_max_pay_for_order, timestamp) AS plan_max_pay_for_order,
    argMax(fact_predict_orders, timestamp) AS fact_predict_orders,
    argMax(fact_pay_for_order, timestamp) AS fact_pay_for_order
FROM default_db.plan_fact_stats
WHERE adv_id = %(adv_id)s
GROUP BY adv_id
