# pipeline graph meta

updated_at_utc: 2026-08-13T09:39:25Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 302182dfcd9ba13b965d935646cfc380
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 56
source_commit: efc003a83e092207dff1972b36ccda1f4ba9eed4
approved_by_token: resolve-conflicts GO (semantic GRAPH/META rebase merge)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 78d0d0b70d31bdec0c1a2f7fa092c369a69058f094ee800e9b5a9549abb864fb
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  resolve-conflicts GO 2026-08-13T09:39:25Z: rebase pick 14636d5c0 onto
  afa3f4d42 — keep HEAD lifecycle evidence (PA, Scenario, phased verify,
  test-env, F13/F14, Bugbot residual / project-bug-hunt; soft
  /opsx-distribute-brief post-archive only; /opsx-meta-commit;
  /opsx-meta-fix-command-defects). Discarded incoming Corrective V2
  inventory-38 meta as stale. Recomputed names_only inventory 56
  fingerprint 302182dfcd9ba13b965d935646cfc380 via graph_fingerprint.reproduce().
