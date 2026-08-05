# pipeline graph meta

updated_at_utc: 2026-08-04T16:05:52Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: f258e9518d2b3c9ff38f6469c77d7a2e
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 43
source_commit: pending_local
approved_by_token: /opsx-pipeline UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-04 from chat draft: inventory 43 /
  fingerprint f258e9518d2b3c9ff38f6469c77d7a2e via reproduce().
  Added side-lane stubs (evolution, devops, scripts-prepare, scripts,
  supervisor, human-label-display). Patched apply/pyright for include
  hygiene. Soft pyright section notes in-session hygiene. F12 remains
  open (partial apply Post-apply fix). F13 closed on GRAPH nodes (watch
  agent compliance). F14 open (FP counts admin-resolve-conflicts;
  SCOPE-strict would be 42). propose still excluded_by_owner.
  Wrote only GRAPH.md + META.md.
