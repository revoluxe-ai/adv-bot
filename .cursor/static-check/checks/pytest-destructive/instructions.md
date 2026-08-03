# pytest-destructive — instructions

FULL-only wave: live PG/CH (and related) via docker-compose.test.yml fixtures.

From repo root, with env set for this process only:

```bash
export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
export ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m destructive_local
```

Packet COMMAND: `poetry run pytest -m destructive_local` (document ALLOW_* set).

**Orchestrator gate:** MODE=FULL only. Start only if `pytest-integration`
packet `STATUS=PASS`. Otherwise SKIPPED (including all FAST runs).

## Rules

- Never schedule in FAST.
- Do **not** `--deselect` / exclude paths already run earlier in the cascade.
- Do not run pyright, mypy, or other marker suites in this pack.
- Do not pass path `.`.
- Missing Docker / ALLOW_* / infra → STATUS=`BLOCKED` or `ERROR` with severity
  `environment` (visible). Do **not** silent-skip as PASS.

## Parsing

Prefer failed node ids (`path::node`).
Exit 0 → PASS. Non-zero with failures → FAIL.
If unavailable → STATUS=BLOCKED.
