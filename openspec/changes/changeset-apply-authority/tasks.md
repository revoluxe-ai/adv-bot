## Planning gate (this change)

PLANNING_ONLY: false
PLANNING_MERGED: true
PLANNING_MERGE_PR: 459
IMPLEMENTATION_GO: true
SLICE_A_OWNER_MERGED: true (#464 → 6b62da98d)
SLICE_B_IMPLEMENTATION_GO: true (PG ledger only — this instruction)
SLICE_C_PLUS_AUTHORIZED: false
BASELINE_SHA: `origin/stage` at slice cut — refresh at verify

## 0. Planning verification

- [x] 0.1 OpenSpec strict validate `changeset-apply-authority` (planning)
- [x] 0.2 Materialize `scenario-coverage/plan.md` with S01–S35 rows
- [x] 0.3 Planning merged to `stage` (#459)
- [x] 0.4 Owner contract review + receipt lifecycle repairs

## 1. Architecture (planning)

- [x] 1.1 Inventory merged `wb_sky_control_plane` dry-run contract
- [x] 1.2 Proposed ADR `changeset-apply-authority-ownership`
- [x] 1.3 Promoted `campaign-settings-changeset-ownership` ADR on stage

## 2. Slice A — domain vocabulary (**completed**)

- [x] 2.1 `apply/models` types: `ApplyRequestV1`, `DryRunReceiptV1`, `ApplyEvidenceV1`, `ApplyPlanV1`
- [x] 2.2 Pure functions: `pd1`, `cpd1`, idempotency decisions, receipt lifecycle, binding hints
- [x] 2.3 Unit tests + `slice-a-l1-audit.receipt.json` (truthful partial/deferred labels)

## 3. Slice B — PG ledger (**completed pending Owner merge**)

- [x] 3.1 Forward-only Alembic `f9c0a1b2d3e4` for receipt / idempotency / attempt / evidence tables
- [x] 3.2 PG repositories + claim/concurrency semantics (no writer orchestration)
- [x] 3.3 Disposable-Postgres integration tests + `slice-b-l1-audit.receipt.json`

## 4. Slice C — PG policy apply path (**not authorized**)

- [ ] 4.1 `ApplyAuthorityService` orchestration
- [ ] 4.2 `pg.campaign_settings_policy_v1` writer adapter
- [ ] 4.3 Post-apply verification + integration tests

## 5. Slice D — WB writer behind authority (**not authorized**)

- [ ] 5.1 WB mutation class with `UNKNOWN_EXTERNAL_STATE`

## 6. Slice E — REST/MCP (**not authorized**)

- [ ] 6.1 Transport handlers call same service

## 7. Slice F — cross-links (**not authorized**)

- [ ] 7.1 Optional history / decision-memory references

## Scenario coverage

SCENARIO_PLAN: `scenario-coverage/plan.md`
SCENARIOS_TOTAL: 35 (S01–S35)
IMPLEMENTATION_SLICES: A–F (see design.md)
