# pipeline graph meta

updated_at_utc: 2026-07-28T01:43:00Z
scope: ALL_NON_ADMIN_OPSX
source_fingerprint: 36715089212461e01e2291eebdfa7777
fingerprint_strength: names_only
approved_by_token: UPDATE GO
notes: |
  Corrective 2026-07-28: ROUTE_TRACE SCHEMA_VERSION 2 +
  route reconciliation / mismatch hard gate / CHANGED|UNCHANGED
  TASK_DELTA / Owner wait / Route D target / episode closure gate.
  GRAPH adds blocked_route_mismatch + blocked_missing_route_target.
  Prior:
  UPDATE GO after Owner GO UPDATE LIVE ORCHESTRATION ROUTING.
  Classify-first: materialize→claim→classify→Route A|B|C|D.
  Spec route: /opsx-update → TASK_DELTA → /opsx-apply | /opsx-fix-bug.
  Durable ROUTE-TRACE.jsonl + LEDGER ## ROUTE_STATE.
  RED+Owner GO for both fix-bug and bug-episode apply.
  /opsx-update ≠ production GO; task delta ≠ auto apply permission.
  GRAPH remains navigation_snapshot_only (not policy SoT).
  Inventory 26; prior F1–F9 / FANIN / project-bug-hunt kept.
  Bodies partially NOT_OPENED_BUDGET.
