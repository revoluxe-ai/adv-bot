# pytest-integration — instructions

Full safe integration suite (no destructive fixtures).

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration
```

Packet COMMAND: `poetry run pytest -m integration`

**Orchestrator gate:** start only if `pytest-unit` packet `STATUS=PASS`.
If unit is FAIL/BLOCKED/ERROR → do **not** run this check (`SKIPPED`).

## Rules

- Marker `integration` only — conftest must keep `destructive_local` out.
- Do **not** `--deselect` / exclude paths already run in `pytest-targeted`.
- Do not run pyright, mypy, unit suite, or destructive.
- Do not pass path `.` (keeps `pytest.ini` `testpaths = tests`).
- If unavailable → STATUS=BLOCKED.

## Parsing

Prefer failed node ids (`path::node`).
Missing infra → severity `environment` (or `collection-error`).
Exit 0 → PASS. Non-zero with failures → FAIL.
