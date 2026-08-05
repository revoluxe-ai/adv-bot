# pipeline graph meta

updated_at_utc: 2026-08-05T04:13:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 116be47aa5665f6a53713f2a92ce1393
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 44
source_commit: pending_local
approved_by_token: /opsx-pipeline UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-05 from chat draft: inventory 44 /
  fingerprint 116be47aa5665f6a53713f2a92ce1393 via reproduce().
  Confirmed /opsx-doctor simplified CHECK|GO leftover hygiene + states/
  transitions; F15 (empty-without-archive not GC). F12 open; F13/F14
  unchanged. Wrote only GRAPH.md + META.md.
