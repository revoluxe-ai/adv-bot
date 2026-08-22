## 1. Tests-first: SQL-contract для qualification

- [x] 1.1 Добавить unit SQL-contract тест на issued SQL пути
  `get_keyword_statistic_clickhouse` (перехват `client.query`, не полный mock
  самой функции): MUST требовать `default_db.mv_clusters_daily_agg` в тексте
  SQL (spec: `clickhouse-query-database-qualification` — Qualification
  changes are proven via issued SQL). Docstring теста на русском со ссылкой
  на capability.
- [x] 1.2 Убедиться, что текущий RED ожидаем при unqualified
  `FROM mv_clusters_daily_agg` (characterization до правки production).

## 2. Восстановление qualification в production SQL

- [x] 2.1 В `app/modules/wb_adv_updater/data_manager.py` восстановить
  `FROM default_db.mv_clusters_daily_agg` в
  `get_keyword_statistic_clickhouse`; синхронизировать docstring/комментарии
  с фактом квалификации (убрать утверждение «без database-prefix /
  client.database-only»).
- [x] 2.2 Прогнать тест из §1 и подтвердить GREEN на issued SQL.

## 3. Hunt того же класса (точечно)

- [x] 3.1 Bounded hunt: недавние/соседние CH SQL readers с снятым
  `default_db.` или голым `FROM <table|mv_*>` в application query paths
  (тот же класс регрессии; не массовый rewrite всех CH readers).
- [x] 3.2 Для каждого найденного KEEP-места: восстановить
  `default_db.<object>` и добавить/расширить SQL-contract unit на issued SQL
  (без `SQL_REWRITE_MOCKED_AWAY`).
  _(Hunt: других KEEP-мест того же класса в `wb_adv_updater` / seam-комментариях
  не найдено; единственный regression path — `get_keyword_statistic_clickhouse`.)_

## 4. Verification

- [x] 4.1 Targeted `poetry run pytest -m unit` по затронутым тест-файлам /
  модулю `wb_adv_updater` (и новым SQL-contract тестам).
- [x] 4.2 При затронутых типах — `poetry run pyright-strict` на изменённых
  путях; `git diff --check` на diff change.
- [x] 4.3 Кратко зафиксировать в change summary: intent = вернуть
  qualification (не «убрать DB»); deferred env/mass-unqualify не трогались.
  → см. `APPLY_SUMMARY.md`.
