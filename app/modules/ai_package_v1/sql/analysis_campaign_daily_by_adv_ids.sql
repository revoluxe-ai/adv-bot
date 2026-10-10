-- ============================================================================
-- analysis_campaign_daily_by_adv_ids.sql
-- ============================================================================
-- Назначение: одно чтение дневных фактов ног пакета до номинальной границы
--   анализа. Последняя version на пару adv_id+date. Не узкий CSV периода
--   вызывающей стороны и не разрез на каждое окно.
-- Таблица(и): default_db.full_adv_wb_stat
-- Параметры: %(end_date)s — верхняя включительная дата (UTC-дата сборки);
--   %(adv_ids)s — физические идентификаторы ног пакета
-- Вызывается: ChAnalysisCampaignReader.fetch_daily_facts_with_client
-- ============================================================================
SELECT
    adv_id,
    date,
    argMax(views, version) AS views,
    argMax(clicks, version) AS clicks,
    argMax(spend, version) AS spend,
    argMax(added_to_cart, version) AS added_to_cart,
    argMax(orders, version) AS orders,
    argMax(sum_price_orders, version) AS sum_price_orders
FROM default_db.full_adv_wb_stat
WHERE date <= toDate(%(end_date)s)
  AND adv_id IN %(adv_ids)s
GROUP BY adv_id, date
ORDER BY adv_id, date
