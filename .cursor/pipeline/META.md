# pipeline graph meta

updated_at_utc: 2026-07-30T12:17:37Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 78bbacb3fcee9523e0bdf73df1a18a5d
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 35
source_commit: 7fbce8b13701c946da00f05997f59ab1ca844c60
approved_by_token: UPDATE GO (reuse UPDATE_DRAFT_READY 0b93aa38)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: unchanged_this_increment
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-30T12:17:37Z: materialize antipattern-gate +
  bug-debt-board (inventory 35); soft chain pyright → ecc → optional
  perf → antipattern → static; demote performance_pass→static as primary;
  F11 closed; F12 SOFT_CHAIN_CONTRACT_LAG open; retain NOT_OPENED_BUDGET
  existing GRAPH entries. Fingerprint matches approved draft name list
  (printf order; test.md before test-triage.md).
  Prior: CLOSE_POLICY / BUG_EPISODE_FORK (2026-07-30T09:05:00Z);
  performance-review (2026-07-30T04:38:13Z).
