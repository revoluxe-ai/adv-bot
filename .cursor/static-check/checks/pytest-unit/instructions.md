# pytest-unit — instructions

From repo root (full unit suite — pytest-xdist):

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal
```

Packet COMMAND: `poetry run pytest -m unit -n 8 --dist=worksteal`

**Orchestrator gate:** start only if `pytest-targeted` packet `STATUS=PASS`
(including PASS with `not_applicable_no_related_tests`).
If targeted is FAIL/BLOCKED/ERROR → do **not** run this check (`SKIPPED`).

## Rules

- Do **not** `--deselect` / exclude paths already run in `pytest-targeted`.
  Targeted is early-stop only; this wave is the full marker suite gate.
- Do not run pyright, mypy, integration, destructive, or bare `pytest`.
- Do not drop `-n` / `--dist` for this check (full suite).
- If unavailable → STATUS=BLOCKED.

## Parsing

Prefer failed node ids (`path::node`).
Collection problems → severity `collection-error`.
Exit 0 → PASS. Non-zero with failures → FAIL.
