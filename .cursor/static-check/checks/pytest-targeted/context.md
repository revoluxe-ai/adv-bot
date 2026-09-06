# pytest-targeted — context

- Early feedback on dirty working-tree changes before full marker suites.
- Dirty scope = entire working tree (status), not `/opsx-commit` staged-only
  grouping. Inference heuristic matches `/opsx-commit` «Infer related tests»
  (adjacent / mirrored `tests/` paths); commit FAIL_CLOSED for missing related
  tests does **not** apply here — static-check v1 uses PASS + note.
- Marker `unit` = no real DB/Redis/ClickHouse; `integration` = safe multi-module
  (conftest strips `destructive_local`). Never run destructive in this pack.
- **Prefilter** `destructive_local`-only modules **before** any Shell; never
  exclude-and-rerun mid-check. ≤1 invocation per non-empty bucket.
- Empty bucket after prefilter → skip (`bucket_empty_skipped:*`). Scheduled
  run with pytest exit 5 / no tests collected → PASS +
  `bucket_empty_collection:*`, not FAIL/restart.
- Path args must stay under `tests/` so `pytest.ini` testpaths stay coherent.
- Suite waves (`pytest-unit`, `pytest-integration`, `pytest-destructive`) must
  re-include the same tests; do not deselect dirty paths after targeted PASS.
