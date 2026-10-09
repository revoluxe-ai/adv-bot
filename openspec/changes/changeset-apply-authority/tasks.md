## Lifecycle (close)

PLANNING_ONLY: false
PLANNING_MERGED: true
PLANNING_MERGE_PR: 459
IMPLEMENTATION_GO: true
V1_SCOPE: PG_ONLY_SLICES_A_B_C
OWNER_SCOPE_DECISION: OPTION_A_PG_ONLY_V1
SLICE_A_OWNER_MERGED: true (#464)
SLICE_B_OWNER_MERGED: true (#466)
SLICE_C_OWNER_MERGED: true (#467)
BASELINE_SHA: `c9fdf9ce1a00a70d8535877ef618229d48754fca` (pre-archive verify)

## 0. Planning verification

- [x] 0.1 OpenSpec strict validate `changeset-apply-authority`
- [x] 0.2 Materialize `scenario-coverage/plan.md` with S01–S35 rows
- [x] 0.3 Planning merged to `stage` (#459)
- [x] 0.4 Owner contract review + receipt lifecycle repairs

## 1. Architecture (planning)

- [x] 1.1 Inventory merged `wb_sky_control_plane` dry-run contract
- [x] 1.2 ADR `changeset-apply-authority-ownership` (promote on archive)
- [x] 1.3 Promoted `campaign-settings-changeset-ownership` ADR on stage

## 2. Slice A — domain vocabulary

- [x] 2.1 `apply/models` types
- [x] 2.2 Pure functions: `pd1`, `cpd1`, idempotency, receipt lifecycle
- [x] 2.3 Unit tests + `slice-a-l1-audit.receipt.json`

## 3. Slice B — PG ledger

- [x] 3.1 Alembic `f9c0a1b2d3e4`
- [x] 3.2 PG repositories + claim/concurrency
- [x] 3.3 Integration tests + `slice-b-l1-audit.receipt.json`

## 4. Slice C — PG policy apply path

- [x] 4.1 `ApplyAuthorityService` orchestration
- [x] 4.2 `pg.campaign_settings_policy_v1` writer
- [x] 4.3 Post-apply verification + integration tests + `slice-c-l1-audit.receipt.json`

## 5–7. Future changes (not in this archive)

- [x] 5.0 Record `external-wb-apply-authority` boundary (`FUTURE_BOUNDARIES.md`) — **not implemented**
- [x] 6.0 Record `apply-transport-adapters` boundary — **not implemented**
- [x] 7.0 Record optional history/decision-memory links — **not implemented**

## 8. Archive close

- [x] 8.1 Reconcile docs + normative spec to PG-only V1
- [x] 8.2 Change-level `scenario-coverage/certify.receipt.json`
- [x] 8.3 Promote ADR to `openspec/decisions/`
- [x] 8.4 `openspec archive changeset-apply-authority` + post-archive verify

## Scenario coverage

SCENARIO_PLAN: `scenario-coverage/plan.md`
SCENARIOS_TOTAL: 35
V1_IMPLEMENTATION_SLICES: A, B, C
FUTURE_SLICES: D, E, F (separate changes)
