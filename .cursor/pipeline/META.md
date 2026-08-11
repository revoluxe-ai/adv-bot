# pipeline graph meta

updated_at_utc: 2026-08-11T03:07:21Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: cb7ea54dea1568434d9b206f15b63012
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 55
indexed_commands: 55
source_commit: f8bd51fcc837f0164f12d1c83b3c6c957aaeab49
approved_by_token: UPDATE GO (reuse UPDATE_DRAFT_READY MAX_INDEX + include /opsx-propose)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: unchanged_this_increment
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-11T03:07:21Z MAX_INDEX: materialize all 55 not-admin
  commands (meta plane, projectize/adapt, commit-all, evolution, devops,
  supervisor, propose). Owner removed F5 graph exclusion of /opsx-propose.
  Fingerprint unchanged (names_only cb7ea54dea1568434d9b206f15b63012).
  F5 closed as exclusion; F12/F13 open; F15 meta/admin remap; F16 supervisor
  allowlist lag; F17 closed (prior inventory-only gap). Deep fields for some
  meta helpers remain NOT_OPENED_BUDGET where only grep/header evidence.
  Prior: UPDATE GO 2026-08-09T05:34:03Z test-env (F14).
