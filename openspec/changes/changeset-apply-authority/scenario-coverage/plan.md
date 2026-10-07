# Scenario coverage plan

CHANGE_ID: changeset-apply-authority
MODE: plan
PLAN_STATUS: ready
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true

Planning evidence only. Does not assert tests exist or PASS.

## GENERATED_FROM

Recompute `PLAN_EVIDENCE_ID` at certify from UTF-8 LF identity blob:

```text
changeset-apply-authority
plan
design.md:<sha256>
specs/changeset-apply-authority/spec.md:<sha256>
owner-contract.md:<sha256>
```

## Global evidence rules

RUNTIME_SCENARIO_SEAM: future `ApplyAuthorityService` + real `validate_changeset` /
`dry_run` reuse; V1 PG writer integration tests use disposable PG.

THIN_ENDS: forbidden-adapter spies (WB write clients, `apply_adv_excel_rows`,
shop-runner mutation, direct MCP writer).

PRODUCTION_ENTRYPOINT (target): `app.modules.wb_sky_control_plane.apply.service.ApplyAuthorityService.apply`

## Slice map

| Scenario | Slice |
|----------|-------|
| S01 | C |
| S02 | A, C |
| S03 | B, C |
| S04 | A, B |
| S05 | A, C |
| S06 | A, C |
| S07 | A |
| S08 | C |
| S09 | A, C |
| S10 | D |
| S11 | D |
| S12 | C |
| S13 | C |
| S14 | C |
| S15 | E |
| S16 | E + lint/import policy |
| S17 | B |
| S18 | F |
| S19 | F |
| S20 | A |

## Rows

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S01
  REQUIREMENT: Dry-run success is not apply permission — exact bound apply succeeds
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S02
  REQUIREMENT: Stale state rejection
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S03
  REQUIREMENT: Idempotency replay
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S04
  REQUIREMENT: Idempotency conflict
  SLICE: A, B
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S05
  REQUIREMENT: Capability revalidation
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S06
  REQUIREMENT: Unauthorized actor
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S07
  REQUIREMENT: Digest mismatch
  SLICE: A
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S08
  REQUIREMENT: PG atomic multi-op
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S09
  REQUIREMENT: Validation failure zero writes
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S10
  REQUIREMENT: External writer rejection
  SLICE: D
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S11
  REQUIREMENT: UNKNOWN_EXTERNAL_STATE
  SLICE: D
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S12
  REQUIREMENT: Verification match
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S13
  REQUIREMENT: Verification mismatch
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S14
  REQUIREMENT: post_state_token emitted
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S15
  REQUIREMENT: Transport parity
  SLICE: E
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S16
  REQUIREMENT: MCP writer bypass forbidden
  SLICE: E
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S17
  REQUIREMENT: Immutable evidence
  SLICE: B
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S18
  REQUIREMENT: History boundary
  SLICE: F
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S19
  REQUIREMENT: Decision memory boundary
  SLICE: F
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S20
  REQUIREMENT: Unknown version/op fail closed
  SLICE: A
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S21
  REQUIREMENT: Trusted invocation context
  SLICE: A
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S22
  REQUIREMENT: Idempotent replay authorization
  SLICE: A, B
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S23
  REQUIREMENT: Receipt consumed
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S24
  REQUIREMENT: Pre-write receipt not consumed
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S25
  REQUIREMENT: Attempt vs evidence immutability
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S26
  REQUIREMENT: PG atomicity settings+evidence
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S27
  REQUIREMENT: UNKNOWN_INTERNAL_COMMIT
  SLICE: C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S28
  REQUIREMENT: Authz vs capability
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S29
  REQUIREMENT: Legacy bypass acknowledgment
  SLICE: A (doc), C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S30
  REQUIREMENT: Stale receipt permanent invalidation
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S31
  REQUIREMENT: ABA receipt safety
  SLICE: A, B
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S32
  REQUIREMENT: Unauthorized preserves receipt
  SLICE: A, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S33
  REQUIREMENT: Digest mismatch preserves receipt
  SLICE: A
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S34
  REQUIREMENT: Commit unknown blocks retry
  SLICE: B, C
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: S35
  REQUIREMENT: Idempotent replay no mutation
  SLICE: B, C
  ROW_PLAN: required

SCENARIOS_TOTAL: 35
LIFECYCLE_GAPS: none at planning
SPEC_SCENARIO_MISSING: none
