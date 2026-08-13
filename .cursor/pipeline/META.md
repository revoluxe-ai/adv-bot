# pipeline graph meta

updated_at_utc: 2026-08-11T14:44:35Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: d006b15039bc6f2e04f3e96e16cb52bb
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 57
indexed_commands: 57
source_commit: 19260f0a375b9f8adfd56f008a70229eef34805d
approved_by_token: UPDATE GO (reuse UPDATE_DRAFT_READY — index /opsx-owner-contract-review + soft OCR edges)
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: unchanged_this_increment
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-08-11T14:44:35Z: inventory 57 (fingerprint
  d006b15039bc6f2e04f3e96e16cb52bb names_only). Index
  /opsx-owner-contract-review; add owner_contract_* states; soft
  change_scaffolded→OCR→continue/ff and REPAIR via OWNER_REVIEW_HANDOFF;
  close F18; refresh META count/fingerprint lag vs prior body.
  F12/F13/F15/F16 remain open. Deep fields for unopened commands stay
  NOT_OPENED_BUDGET. Prior: UPDATE GO 2026-08-11T03:07:21Z MAX_INDEX.
