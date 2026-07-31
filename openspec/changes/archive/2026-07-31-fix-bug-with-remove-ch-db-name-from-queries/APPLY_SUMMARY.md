# Apply summary — fix-bug-with-remove-ch-db-name-from-queries

**Intent:** вернуть/удержать квалификацию `default_db.` в тексте CH SQL
(имя каталога change историческое — не «убрать DB из queries»).

**Done:**
- Restored `FROM default_db.mv_clusters_daily_agg` in
  `get_keyword_statistic_clickhouse` (`data_manager.py`).
- SQL-contract unit:
  `tests/modules/wb_adv_updater/test_get_keyword_statistic_clickhouse_sql_contract.py`
  (capture `client.query`; RED then GREEN).
- Bounded hunt: no additional same-class KEEP holes in `wb_adv_updater`
  CH readers / seam comments.

**Not done (deferred / out of scope):**
- env → `client.database` as sole DB name resolver;
- mass unqualify / mass rewrite of all CH readers;
- promoting env-policy ADL beyond proposed qualification decision.

**Gates this session:**
- `poetry run pytest -m unit tests/modules/wb_adv_updater/ …` — 98 passed
- `poetry run pyright-strict app/modules/wb_adv_updater/data_manager.py` — 0 errors
- `git diff --check` on touched paths — clean
