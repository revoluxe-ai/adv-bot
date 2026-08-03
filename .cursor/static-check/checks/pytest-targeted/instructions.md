# pytest-targeted — instructions

Early pytest gate over the **git working tree** (staged + unstaged dirty paths).
Path-focused, no xdist. Never runs `destructive_local`.

## Scope (dirty + related)

1. Inventory dirty paths: `git status --short` (working tree, not commit-group
   staged-only).
2. Collect candidate tests:
   - dirty files under `tests/**` that look like pytest modules
     (`test_*.py`, `*_test.py`, or packages with tests);
   - for dirty production under `app/**` (and similar production trees), infer
     related tests using the same heuristic as `/opsx-commit` «Infer related
     tests» (adjacent / mirrored path under `tests/`, name-stem matches).
3. Split candidates by marker intent when known from path layout:
   - prefer `tests/unit/**` and unmarked unit-style paths → unit bucket;
   - prefer `tests/integration/**` → integration bucket;
   - never put `destructive_local`-only modules into this check.

## Commands

From repo root. Prefer separate runs when both buckets are non-empty:

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit <unit_paths...>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration <integration_paths...>
```

Packet COMMAND: list the exact `poetry run pytest …` invocations used (no xdist).

## Not-applicable (PASS with note)

If there are no related Python test paths (clean tree for prod/tests, or
production dirty with no inferred tests):

- STATUS=`PASS`
- NOTES must include `not_applicable_no_related_tests` and/or
  `no_related_tests_inferred`
- Do **not** FAIL_CLOSED in v1 for missing related tests

## Gates / prohibitions

- Do not run pyright, mypy, full unit/integration suites, or destructive.
- Do not use `-n` / `--dist` (path-focused only).
- Do not pass path `.` (keeps `pytest.ini` `testpaths = tests`).
- Orchestrator: later suite waves must **not** `--deselect` / exclude these
  paths — targeted is early-stop only; suite waves re-run the full marker set.

## Parsing

Prefer failed node ids (`path::node`).
Collection problems → severity `collection-error`.
Any non-zero from a real targeted run → FAIL.
Not-applicable path above → PASS with note.
If unavailable → STATUS=BLOCKED.
