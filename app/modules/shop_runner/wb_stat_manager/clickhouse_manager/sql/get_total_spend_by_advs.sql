-- ============================================================================
-- get_total_spend_by_advs.sql
-- ============================================================================
-- Назначение: суммарный расход кампаний за ВСЮ историю (абсолютный/lifetime
--             spend) без ограничения по дате. Используется гейтом абсолютного
--             лимита бюджета РК: пауза кампаний и блокировка автопополнений.
-- Таблица(и): default_db.full_adv_wb_stat
-- Параметры: %(adv_ids)s — список adv_id кампаний (Авто и/или Аукцион)
-- Агрегация: внутри (adv_id, date) берётся последняя версия строки
--            (argMax по version), затем сумма по всем дням и кампаниям
-- Вызывается: full_wb_adv_stat.get_total_spend_by_advs —
--             AutoAdvActiveControlService, AutoBudgetService, меню РК
-- ============================================================================
SELECT
    COALESCE(SUM(latest_spend), 0.0) AS total_spend
FROM (
    SELECT
        adv_id,
        date,
        argMax(spend, version) AS latest_spend
    FROM default_db.full_adv_wb_stat
    WHERE adv_id IN %(adv_ids)s
    GROUP BY adv_id, date
)
