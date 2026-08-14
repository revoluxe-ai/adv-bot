# pipeline graph meta

updated_at_utc: 2026-08-09T05:34:03Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: cb7ea54dea1568434d9b206f15b63012
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 55
source_commit: f8bd51fcc837f0164f12d1c83b3c6c957aaeab49
approved_by_token: UPDATE GO (reuse UPDATE_DRAFT_READY INCREMENTAL /opsx-test-env)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: c282593ccfc8d4b6d50c2406a1269ee12cdab3306ae9e3c629f05cb069b1bdef
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-09T05:34:03Z INCREMENTAL: materialize /opsx-test-env +
  local_test_env_* states/transitions; soft chain antipattern → test-env UP
  → static FULL → test-env DOWN; F14 closed; F13 TEST_ENV_COMPANION_LAG open
  (static-check/supervisor/test companions); F12 still open; inventory 55
  fingerprint cb7ea54dea1568434d9b206f15b63012 (names_only). Other new
  command files (meta-*, supervisor, devops, …) inventory-counted only —
  NOT_OPENED_BUDGET for full command sections.
  Prior: UPDATE GO 2026-07-30T12:17:37Z antipattern-gate + bug-debt-board
  (inventory 35; F11 closed; F12 open).
