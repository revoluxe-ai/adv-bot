# pipeline graph meta

updated_at_utc: 2026-07-28T22:30:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 4a43ef4d581b5dde966bd4c340de6753
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 28
source_commit: fb009fd6645ee3b20774f670504cad4eeb4bbc75
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-28T22:30:00Z: Owner activation of invariant-family fanout
  V8–V10 on /opsx-bug-team. PIPELINE_GENERATION=ACTIVE_V1_WITH_INVARIANT_FANOUT_V10;
  BUG_FAMILY_FANOUT_ENABLED=true. Graph now indexes ROOT GREEN → invariant
  capture → hunt → relation → same-invariant fanout → integration → family
  GREEN → family fan-in → learning → closure. Controlling independent verdict
  INDEPENDENT_EXECUTION_IDENTITY_TARGETED_RERUN_PASS. Commit/push/deploy remain
  FORBIDDEN. Command-native v2 planned separately.
