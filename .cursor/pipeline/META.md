# pipeline graph meta

updated_at_utc: 2026-07-29T05:18:39Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 4c572a4fbfabce2cea414878b844f11e
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 30
source_commit: 835e7ea19897ad5ca5d535fe987be6aa86f78502
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 02f6c582026be14c9868249d1c05d8f59e5cb10b666176dd4fbd18d1714d01cd
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-29T05:18:39Z: Added /opsx-external-call-coverage to
  not-admin graph (post pyright-strict-coverage, before static-check/verify).
  Inventory 30 nodes; fingerprint independently reproduced.
