# Fixtures: Task Generation Readiness

Process-only regression for:

```text
resolved design/spec/decisions
  → DRAFT_TASKS
  → NORMATIVE_PRESERVATION_CHECK
  → TASK_GENERATION_READINESS
  → tasks.md  (/opsx-continue ≡ /opsx-ff)
```

Commands under test:

- `/opsx-continue` / `/opsx-ff` (when artifact is `tasks`)
- contract: `.cursor/pipeline/contracts/TASK_GENERATION.md`

## Authority invariant

```text
TASKS MUST IMPLEMENT DESIGN, NOT COMPLETE DESIGN
TASK GENERATION MUST PRESERVE UPSTREAM NORMATIVE MODALITY
same upstream artifacts → semantically equivalent tasks
MUST/MUST NOT modality preserved (post-generation check required)
conditional branches preserved (no collapse to MAY)
LEGACY_BASELINE ≠ TARGET_REGRESSION
```

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-unresolved-architecture.md` | architecture fork | BLOCKED TECHNICAL_DESIGN_UNRESOLVED |
| 02 | `02-legacy-vs-target.md` | evidence roles | LEGACY_BASELINE + TARGET_REGRESSION |
| 03 | `03-must-preservation.md` | T1 MUST | Auto MUST start (not MAY) |
| 04 | `04-must-not-preservation.md` | T2 MUST NOT | MUST NOT force start preserved |
| 05 | `05-continue-ff-equivalence.md` | T8 continue≡ff | continue ≡ ff tasks |
| 06 | `06-regression-auto-shelf-sample.md` | T7 real sample | no MAY-start collapse; both branches + epoch |
| 07 | `07-conditional-branch-preservation.md` | T3 branches | both MUST / MUST NOT branches explicit |
| 08 | `08-epoch-coupling.md` | T4 epoch | epoch only after actual start |
| 09 | `09-conflicting-upstream-modality.md` | T5 conflict | BLOCKED UPSTREAM_NORMATIVE_CONFLICT |
| 10 | `10-post-generation-modality-drift.md` | T6 post-check | BLOCKED NORMATIVE_MODALITY_DRIFT |

## Non-goals

- Do not edit product `openspec/changes/auto-shelf-exhausted-pause-retest/**`
  as part of applying this fixture pack.
- Do not change `/opsx-new`, owner-contract-review, scenario-coverage,
  design-generation, Product Acceptance, apply/verify/archive in these fixtures.
