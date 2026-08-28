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
3. **Prefilter (mandatory, before any Shell):** drop candidates that are
   `destructive_local`-only (known from path layout, module docstring/marker,
   or pack knowledge such as modules that only run under destructive). Never
   schedule them in either bucket. Do **not** discover mid-run then exclude
   and re-invoke pytest.
4. Split remaining candidates by marker intent when known from path layout:
   - prefer `tests/unit/**` and unmarked unit-style paths → unit bucket;
   - prefer `tests/integration/**` → integration bucket.

## Commands

From repo root. At most **one** `run.sh` invocation per non-empty bucket per
`CHECK_ID` (unit ≤1, integration ≤1). No exclude-and-rerun /
«перезапускаю …-bucket» loops.

If after prefilter a bucket has zero paths → **do not** run that bucket;
record `bucket_empty_skipped:<unit|integration>` in NOTES.

When both buckets are non-empty after prefilter:

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit <unit_paths...>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration <integration_paths...>
```

Packet COMMAND: list only the exact `poetry run pytest …` invocations actually
run (0–2; no xdist).

## Not-applicable (PASS with note)

If there are no related Python test paths after prefilter (clean tree for
prod/tests, production dirty with no inferred tests, or all candidates were
destructive-only):

- STATUS=`PASS`
- NOTES must include `not_applicable_no_related_tests` and/or
  `no_related_tests_inferred` and/or `bucket_empty_skipped:*` as applicable
- Do **not** FAIL_CLOSED in v1 for missing related tests

## Empty collection / pytest exit 5 (PASS with note — not FAIL, not restart)

If a **scheduled** bucket run exits with pytest exit code **5** / «no tests
collected» and **no** failed node ids:

- Treat as bucket N/A (same PASS path as not-applicable for that bucket)
- NOTES must include `bucket_empty_collection:<unit|integration>`
- Do **not** FAIL
- Do **not** exclude paths and re-invoke pytest for the same bucket

## Gates / prohibitions

- Do not run pyright, mypy, full unit/integration suites, or destructive.
- Do not use `-n` / `--dist` (path-focused only).
- Do not pass path `.` (keeps `pytest.ini` `testpaths = tests`).
- Do not mid-check exclude + rerun (prefilter only, before first Shell).
- Orchestrator: later suite waves must **not** `--deselect` / exclude these
  paths — targeted is early-stop only; suite waves re-run the full marker set.

## Parsing

Prefer failed node ids (`path::node`).
Collection problems on **intended** modules → severity `collection-error` → FAIL.
Real targeted run with failed nodes / non-zero **with diagnostics** → FAIL.
Exit 5 / empty collection with no failed nodes → PASS + `bucket_empty_collection:*`
(see above), not FAIL.
Not-applicable / all buckets skipped empty → PASS with note.
If unavailable → STATUS=BLOCKED.
