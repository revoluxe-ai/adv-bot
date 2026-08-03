# pipeline graph meta

updated_at_utc: 2026-08-03T06:14:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 29c989e65a123ae57c77d674bf3b7189
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 38
source_commit: pending_local
approved_by_token: design-command GO OPTION_A (opsx-distribute-brief)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: a9fe5477ae1229fe7e1e91b441a109a94638d5a54c6baa7f702ecd91bc38e024
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  design-command GO OPTION_A 2026-08-03: materialize /opsx-distribute-brief
  (post-archive soft companion for client/CS distribution brief); archive
  soft NEXT; consult front-door route; inventory 38; fingerprint
  29c989e65a123ae57c77d674bf3b7189. Prior META inventory 35 was stale vs disk.
  F12 SOFT_CHAIN_CONTRACT_LAG remains open from prior UPDATE GO.
