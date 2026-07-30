# pipeline graph meta

updated_at_utc: 2026-07-30T09:05:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: pending_names_refresh
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 33
source_commit: local_uncommitted_close_policy
approved_by_token: DESIGN_GO OPTION_A+BUG_TEAM_HANDBACK+SOLO_WALK+PIPELINE_COMPANION
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: unchanged_this_increment
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  DESIGN GO 2026-07-30: CLOSE_POLICY + BUG_EPISODE_FORK soft section;
  GREEN → team handback default; solo walk ALSO_OK; NO_SILENT_RETURN;
  Owner-block explore hint; apply never closed_fixed; pipeline ALSO_OK field.
  Prior: performance-review (2026-07-30T04:38:13Z).
