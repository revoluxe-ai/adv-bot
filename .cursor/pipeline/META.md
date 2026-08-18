# pipeline graph meta

updated_at_utc: 2026-08-18T15:01:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 78bbacb3fcee9523e0bdf73df1a18a5d
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 35
source_commit: 8917818ef
approved_by_token: UPDATE GO (2026-08-18T15:01:00Z)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: unchanged_this_increment
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-18T15:01:00Z: refreshed audit command entries for
  WORKTREE/REF target semantics and closed F13 DIRTY_WORKTREE_AUDIT_TARGET.
  Inventory remains 35; soft chain pyright → ecc → optional perf →
  antipattern → static; F12 SOFT_CHAIN_CONTRACT_LAG remains open; retain
  NOT_OPENED_BUDGET existing GRAPH entries. Fingerprint matches the approved
  names-only inventory.
  Prior: CLOSE_POLICY / BUG_EPISODE_FORK (2026-07-30T09:05:00Z);
  performance-review (2026-07-30T04:38:13Z).
