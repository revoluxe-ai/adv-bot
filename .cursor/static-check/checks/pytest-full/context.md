# pytest-full — RETIRED

Historical pack for bare `poetry run pytest`. Removed from registry.
See `pytest-targeted`, `pytest-unit`, `pytest-integration`, `pytest-destructive`.# pytest-full — context
- Includes unit + integration and may need Docker/DB/local services.
- Honest environment failures beat fake "test-failure" labels.
- Heavier than unit; expected only in MODE=FULL.
- Invoke `poetry run pytest` (no path arg) so `testpaths = tests` applies.
  Do **not** pass `.` — that overrides testpaths and may collect `.tmp/**`
  harness / docker-volume trees (collection errors, not missing libs).
- **Destructive cache (default `CACHE_MODE=dev`):** honor orchestrator
  `CACHE_MODE` and
  `.cursor/static-check/contracts/destructive-selective-cache.md`.
  Use `.cursor/static-check/bin/destructive_cache_plan.py` before running
  any `destructive_local` nodes. `CACHE_OFF` / `CACHE_FORCE` only when
  passed from `/opsx-static-check`. `CACHE_HIT` ≠ archive EXECUTED green.