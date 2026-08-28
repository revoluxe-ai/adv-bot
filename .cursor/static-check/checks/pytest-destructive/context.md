# pytest-destructive — context

- Marker `destructive_local` = live Postgres/ClickHouse (and related) via
  `docker-compose.test.yml` fixtures; requires explicit ALLOW_* env flags.
- Scheduled only in MODE=FULL after `pytest-integration` PASS.
- Heavier and riskier than integration — keep fail-closed on missing env
  (BLOCKED/ERROR), never silent PASS.
- Cascade order: targeted → unit → integration → destructive. Suites do not
  exclude dirty paths covered by targeted.
