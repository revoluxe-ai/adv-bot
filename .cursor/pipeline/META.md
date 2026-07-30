# pipeline graph meta

updated_at_utc: 2026-07-30T04:38:13Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: d8acc1c0ce8e215eb1ef01c39f667f07
fingerprint_strength: names_only
fingerprint_algorithm: md5
fingerprint_input_mode: names_only_newline_joined
inventory_count: 33
source_commit: f04a0bccf2643336eea5a3e4f0660ea344e8637e
approved_by_token: UPDATE GO
inventory_path: .cursor/pipeline/bug-team/controlled-tests/INVENTORY.json
inventory_content_sha256: 9c19b53dcb37c0e5333fd4a78e0c478edc1df98f21599f449a673feaf3c30585
reproduction_command: python -c "import sys; sys.path.insert(0,'.cursor/pipeline/bug-team/runtime'); from graph_fingerprint import reproduce; print(reproduce())"
notes: |
  UPDATE GO 2026-07-30T04:38:13Z: Added /opsx-performance-review and
  /opsx-performance-fix command-nodes, performance_* states, transitions
  (external_call_pass → performance → static-check; FAIL → fix → re-audit),
  soft-recommend section, Terminal recovery bullet, F10 closed.
  Inventory 33; fingerprint d8acc1c0ce8e215eb1ef01c39f667f07 (names_only).
  /opsx-propose remains excluded from recommendations by owner directive.
  Prior: bound-scope (2026-07-29T15:26:39Z); close-external-gap
  (2026-07-29T05:36:55Z).
