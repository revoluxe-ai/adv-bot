# pytest-full — instructions

From repo root.

**Orchestrator gate:** start only if `pytest-unit` packet `STATUS=PASS`.
If unit is FAIL/BLOCKED/ERROR → do **not** run this check (`SKIPPED`).

Honor `CACHE_MODE` from orchestrator (`dev` default on FULL). Contract:
`.cursor/static-check/contracts/destructive-selective-cache.md`.

```text
CACHE_MODE=off|force:
  bash .cursor/static-check/bin/run.sh -- poetry run pytest

CACHE_MODE=dev (default):
  1) bash .cursor/static-check/bin/run.sh -- poetry run pytest -m "not destructive_local"
  2) plan via .cursor/static-check/bin/destructive_cache_plan.py
  3) run only MUST_RUN destructive nodeids (same run.sh wrapper)
```

If planner missing/broken → `CACHE_DEGRADED=yes` and run full
`poetry run pytest` (do not fake PASS). **INTERIM:** never invent
`--deselect` / nodeid skip / “branch already green” without planner
receipt; never claim `CACHE_HIT` while degraded.

Packet COMMAND: exact pytest invocation(s) used (include CACHE_MODE).

Do **not** pass path `.` — it overrides `pytest.ini` `testpaths = tests` and may
collect `.tmp/**` / volume trees.

If unavailable → STATUS=BLOCKED.
Do not run pyright or mypy.

Packet extras when destructive was in plan:
`CACHE_MODE`, `DESTRUCTIVE_TOTAL/RAN/CACHED/FORCED`, `CACHE_DEGRADED`.

## Parsing

Prefer failed node ids.
Missing infra → severity `environment` (or `collection-error`).
Exit 0 → PASS. Non-zero with failures → FAIL.
