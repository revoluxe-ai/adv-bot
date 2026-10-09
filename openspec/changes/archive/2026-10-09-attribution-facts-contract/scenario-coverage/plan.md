# Scenario Coverage Plan

CHANGE_ID: attribution-facts-contract
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-attribution-facts-contract-20261007
LIFECYCLE_STATUS: DERIVED

Planning evidence only. Tests are not claimed executed until apply/verify.

## Lifecycle coverage

`design.md` / `owner-contract.md` slices:

- L1 Domain classification and reconciliation (Slice A)
- L2 Membership as-of resolver (Slice B)
- L3 Observation ingest and nm preservation (Slice B)
- L4 CH persistence and latest projection (Slice C)
- L5 Reader port and coverage metadata (Slice C)
- L6 AI Package / analysis consumption (Slice D)

LIFECYCLE_COVERAGE:

- L1 → S01, S02, S03, S04, S10 — covered
- L2 → S05, S06, S07 — covered
- L3 → S08, S09 — covered
- L4 → S11, S12 — covered
- L5 → S13, S14 — covered
- L6 → S15, S16 — covered

## Architecture and evidence constraints

Architecture Decision References:

- `openspec/decisions/shop-data-source-strategy/decision.md`
- `openspec/specs/grain-preservation/spec.md`
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`
- `openspec/decisions/strict-single-nmid-audit-evidence/decision.md`
- `openspec/changes/attribution-facts-contract/decisions/attribution-facts-collector-ownership/decision.md`

Ownership & Placement:

- Domain pure logic in `app/modules/attribution_facts/`
- Collector/nm preservation per ADR; not in mapper collapse path
- Spend join from `full_adv_wb_stat` only
- AI Package consumes reader port only

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: attribution-facts-contract
SOURCE_SPEC_SHA: TBD_AT_APPLY
PLAN_STATUS: ready

### S01 — DIRECT classification with promoted set

REALITY: unit
GIVEN promoted_nm_ids and nm fact row
WHEN classify
THEN DIRECT

### S02 — LINKED non-promoted nm

REALITY: unit
GIVEN promoted set and other ordered nm with orders
WHEN classify
THEN LINKED

### S03 — UNKNOWN empty promoted set

REALITY: unit
GIVEN empty promoted set
WHEN classify
THEN UNKNOWN not LINKED

### S04 — Reconciliation pass and UNATTRIBUTED

REALITY: unit
GIVEN nm sums match day totals
WHEN reconcile
THEN PASS; UNATTRIBUTED when mismatch policy applies

### S05 — History as-of wins over inventory

REALITY: unit/integration
GIVEN history snapshot for date
WHEN resolve membership
THEN history nmids used

### S06 — Inventory fallback marks PARTIAL

REALITY: unit
GIVEN no history
WHEN inventory fallback
THEN PARTIAL + relation reason code

### S07 — Missing membership fail closed

REALITY: unit
GIVEN no snapshot
WHEN economics requested
THEN no DIRECT/LINKED CPO/DRR numbers

### S08 — Ingest preserves apps/nms tree

REALITY: unit (fixture JSON)
GIVEN raw fullstats with apps/nms
WHEN ingest normalizes
THEN observations per ordered_nm_id

### S09 — Mapper collapse insufficient

REALITY: unit regression
GIVEN DayStats-only path
WHEN ingest attempted
THEN MUST NOT produce COMPLETE nm facts

### S10 — Revision replaces not sums

REALITY: unit
GIVEN two observations same key
WHEN latest projection
THEN second value only

### S11 — CH observation insert idempotent hash

REALITY: integration destructive_local CH
GIVEN duplicate observation_id
WHEN insert
THEN no duplicate logical fact

### S12 — Latest projection argMax

REALITY: integration CH
GIVEN two revisions
WHEN read latest
THEN newer wins

### S13 — Reader returns coverage axes

REALITY: unit
GIVEN PARTIAL scope
WHEN query
THEN coverage_status + reason_codes

### S14 — Cutoff does not imply COMPLETE

REALITY: unit
GIVEN package_cutoff after source_complete_through
WHEN window 1d
THEN not COMPLETE

### S15 — Analysis blocked without facts

REALITY: unit
GIVEN BLOCKED_BY_ATTRIBUTION_FACTS consumer
WHEN facts COMPLETE
THEN metrics emitted

### S16 — Pair aggregate fail closed

REALITY: unit
GIVEN Auto+Search without overlap proof
WHEN pair rollup requested
THEN ATTRIBUTION_SCOPE_MISMATCH

FAIL_CLOSED:

- Missing membership → no DIRECT/LINKED economics
- Reconciliation fail → not COMPLETE
- Buyouts → UNSUPPORTED
