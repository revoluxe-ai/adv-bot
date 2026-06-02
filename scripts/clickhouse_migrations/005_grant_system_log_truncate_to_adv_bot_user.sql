-- ============================================================================
-- 005_grant_system_log_truncate_to_adv_bot_user.sql
-- ============================================================================
-- Назначение: права adv_bot_user на TRUNCATE системных лог-таблиц CH
--   (воркер trunc_system_log_in_clickhouse.py, deployment trunc-system-log-clickhouse).
-- Таблица(и): system.processors_profile_log, system.metric_log, system.query_log,
--   system.text_log, system.asynchronous_metric_log, system.query_metric_log,
--   system.part_log, system.trace_log, system.error_log
-- Параметры: нет
-- Вызывается: вручную clickhouse-client после restore / смены кластера CH
-- ============================================================================

GRANT TRUNCATE ON system.processors_profile_log TO adv_bot_user;
GRANT TRUNCATE ON system.metric_log TO adv_bot_user;
GRANT TRUNCATE ON system.query_log TO adv_bot_user;
GRANT TRUNCATE ON system.text_log TO adv_bot_user;
GRANT TRUNCATE ON system.asynchronous_metric_log TO adv_bot_user;
GRANT TRUNCATE ON system.query_metric_log TO adv_bot_user;
GRANT TRUNCATE ON system.part_log TO adv_bot_user;
GRANT TRUNCATE ON system.trace_log TO adv_bot_user;
GRANT TRUNCATE ON system.error_log TO adv_bot_user;
