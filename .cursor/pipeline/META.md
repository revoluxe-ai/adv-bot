# pipeline graph meta

updated_at_utc: 2026-07-29T15:26:39Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 6b60f06b851ee1655b67a6887111b997
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 31
source_commit: c445c45ab28d3cf6dc3d06f381b2155f927db0fa
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 9c19b53dcb37c0e5333fd4a78e0c478edc1df98f21599f449a673feaf3c30585
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-29T05:36:55Z: Added /opsx-close-external-gap
  (REFACTOR_AND_TEST for PG/CH from coverage packet; no base=).
  Inventory 31 nodes; fingerprint independently reproduced.
  UPDATE GO 2026-07-29T15:26:39Z: Added /opsx-bound-scope command-node and
  post-/opsx-explore advisory transitions for scope bounding + update handoff.
  /opsx-propose remains excluded from recommendations by owner directive.
