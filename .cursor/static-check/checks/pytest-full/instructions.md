# pytest-full — instructions

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest .
```

Packet COMMAND: `poetry run pytest .`

**Orchestrator gate:** start only if `pytest-unit` packet `STATUS=PASS`.
If unit is FAIL/BLOCKED/ERROR → do **not** run this check (`SKIPPED`).

If unavailable → STATUS=BLOCKED.
Do not run pyright or mypy.

## Parsing

Prefer failed node ids.
Missing infra → severity `environment` (or `collection-error`).
Exit 0 → PASS. Non-zero with failures → FAIL.
