# Fixtures: /opsx-planning-review

Process-only regression cases for independent planning-package review.

Command under test: `/opsx-planning-review`  
Contract: `.cursor/pipeline/contracts/PLANNING_REVIEW.md`

## How to use

Dry-run: given the fixture’s durable excerpts, a correct reviewer MUST emit
the `Expected` STATUS / finding fields. Fixtures do **not** authorize writes.

Cross-contract: REPAIR handoff shape MUST be acceptable to `/opsx-update`
`MODE: REPAIR_PLANNING_PACKAGE` once that companion exists (external fix).

## Index

| ID | File | Theme | Expected STATUS |
|----|------|-------|-----------------|
| T1 | `01-clean-package.md` | aligned chain | PASS |
| T2 | `02-must-to-may-design.md` | MUST→MAY in design | REPAIR_REQUIRED |
| T3 | `03-tasks-only-drift.md` | tasks weaken MUST | REPAIR_REQUIRED |
| T4 | `04-unresolved-sot.md` | SoT deferred to apply | REPAIR_REQUIRED or BLOCKED |
| T5 | `05-genuine-owner-ambiguity.md` | A vs B unresolved | NEEDS_OWNER |
| T6 | `06-scenario-gap.md` | material lifecycle uncovered | REPAIR_REQUIRED |
| T7 | `07-scope-drift.md` | OUT_OF_SCOPE in tasks | REPAIR_REQUIRED |
| T8 | `08-stale-tasks.md` | tasks behind repaired design | REPAIR_REQUIRED |
| T9 | `09-self-attestation-false.md` | READY + body MUST→MAY | REPAIR_REQUIRED |
| T10 | `10-read-only.md` | any case | FILES_CHANGED: none |
| T11 | `11-idempotency.md` | twice unchanged | same findings/status |
| T12 | `12-repair-loop.md` | handoff → repair → PASS | second PASS |

## Static matrix

| Pillar / rule | Fixtures |
|---------------|----------|
| SEMANTIC_CONTINUITY | T1, T7 |
| NORMATIVE_PRESERVATION | T2, T3, T9 |
| DESIGN_READINESS | T4 |
| AUTHORITY_AND_SOT | T4 |
| LIFECYCLE / Owner ambiguity | T5 |
| SPEC_COVERAGE | T6 |
| TASK_DECOMPOSITION | T3, T7, T8 |
| STALE_DERIVED_ARTIFACT | T8 |
| Self-attestation not authority | T9 |
| READ_ONLY | T10 |
| Idempotency | T11 |
| Repair loop | T12 |

## Live dry-run note

`auto-shelf-exhausted-pause-retest` may already align Owner/design/tasks on
MAY for conditional start — do not force T2 FAIL on live disk without
checking authoritative Owner modality. Use synthetic T2 for MUST→MAY.
