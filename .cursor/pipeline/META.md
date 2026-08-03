# pipeline graph meta

updated_at_utc: 2026-08-12T21:00:03Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: c8eba2db5fabc15466f48d8e175f40b3
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 57
source_commit: afa3f4d4201b1781672204f3a953460ec241d5de
approved_by_token: resolve-conflicts GO (semantic GRAPH/META rebase merge)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 78d0d0b70d31bdec0c1a2f7fa092c369a69058f094ee800e9b5a9549abb864fb
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  resolve-conflicts GO 2026-08-12T21:00:03Z: rebase pick e49d56999 onto
  afa3f4d42 — keep HEAD lifecycle (PA, Scenario, phased verify, test-env,
  F13/F14, Bugbot residual / project-bug-hunt); preserve soft
  /opsx-distribute-brief post-archive only; normalize process-commit to
  /opsx-meta-commit (admin-command-commit obsolete alias); fix-defects →
  /opsx-meta-fix-command-defects. Discarded both conflict sides' stale
  inventory/fingerprint (55/cb7ea… and 38/29c989…). Recomputed names_only
  inventory 57 fingerprint c8eba2db5fabc15466f48d8e175f40b3.
