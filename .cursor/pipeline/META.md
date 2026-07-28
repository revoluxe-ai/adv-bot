# pipeline graph meta

updated_at_utc: 2026-07-28T04:44:44Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: c4c8dba1b837ed6e01445d82dccae905
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 27
source_commit: d7bfbdc7bdd107d6f35a0913f21864d8b0eb5afd
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 0aa41b0f1e2d29c86d29fc044dcd408bd0eb4b234fc02996d404df3a0e886ac5
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-28T04:44:44Z: Corrective V2 refresh after /opsx-bug-team runtime
  enforcement. Candidate remains NOT_ACTIVE. Inventory 27 nodes;
  fingerprint independently reproduced via graph_fingerprint.reproduce().
