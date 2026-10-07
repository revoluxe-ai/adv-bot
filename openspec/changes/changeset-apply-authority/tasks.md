## Planning gate (this change)

PLANNING_ONLY: true
IMPLEMENTATION_GO: false
BASELINE_SHA: record at verify — `origin/stage` at branch cut

## 0. Planning verification

- [ ] 0.1 `npx @fission-ai/openspec@latest validate changeset-apply-authority --type change --strict`
- [ ] 0.2 Materialize `scenario-coverage/plan.md` with S01–S20 rows
- [ ] 0.3 `git diff --check` clean on planning artifacts
- [ ] 0.4 `git merge-tree $(git merge-base HEAD origin/stage) HEAD origin/stage` → CLEAN
- [ ] 0.5 Owner contract review (`OWNER_CONTRACT_REVIEW_READY`)

## 1. Architecture (planning)

- [x] 1.1 Inventory merged `wb_sky_control_plane` dry-run contract on `origin/stage`
- [x] 1.2 Proposed ADR `changeset-apply-authority-ownership`
- [x] 1.3 Document evidence gaps (`preview_digest`, registry ADR promotion)

## 2. Slice A — domain vocabulary (implementation **not** authorized)

- [ ] 2.1 Add `apply/models` types: `ApplyRequestV1`, `DryRunReceiptV1`, `ApplyEvidenceV1`, `ApplyPlanV1`
- [ ] 2.2 Pure functions: `pd1` preview digest, idempotency key conflict rules, binding validation
- [ ] 2.3 Unit tests for S02, S04, S07, S20 without PG/WB

## 3. Slice B — PG ledger (implementation **not** authorized)

- [ ] 3.1 Forward-only Alembic for apply/idempotency/audit tables
- [ ] 3.2 Receipt persistence API for dry-run (transport change, separate)

## 4. Slice C — PG policy apply path (implementation **not** authorized)

- [ ] 4.1 `ApplyAuthorityService` orchestration
- [ ] 4.2 `pg.campaign_settings_policy_v1` writer adapter
- [ ] 4.3 Post-apply verification + S08, S09, S12–S14 integration tests

## 5. Slice D — WB writer behind authority (implementation **not** authorized)

- [ ] 5.1 Single narrow WB mutation class with `UNKNOWN_EXTERNAL_STATE` (S10–S11)

## 6. Slice E — REST/MCP (implementation **not** authorized)

- [ ] 6.1 Transport handlers call same service (S15–S16)

## 7. Slice F — cross-links (implementation **not** authorized)

- [ ] 7.1 Optional history / decision-memory references (S18–S19)

## Scenario coverage

SCENARIO_PLAN: `scenario-coverage/plan.md`
SCENARIOS_TOTAL: 20 (S01–S20)
IMPLEMENTATION_SLICES: A–F (see design.md)
