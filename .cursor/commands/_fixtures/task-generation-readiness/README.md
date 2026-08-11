# Fixtures: Task Generation Readiness

Process-only regression for:

```text
resolved design/spec/decisions
  → TASK_GENERATION_READINESS
  → tasks.md  (/opsx-continue ≡ /opsx-ff)
```

Commands under test:

- `/opsx-continue` / `/opsx-ff` (when artifact is `tasks`)
- contract: `.cursor/pipeline/contracts/TASK_GENERATION.md`

## Authority invariant

```text
TASKS MUST IMPLEMENT DESIGN, NOT COMPLETE DESIGN
same upstream artifacts → semantically equivalent tasks
MUST/MUST NOT modality preserved
LEGACY_BASELINE ≠ TARGET_REGRESSION
```

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-unresolved-architecture.md` | T1 | BLOCKED TECHNICAL_DESIGN_UNRESOLVED |
| 02 | `02-legacy-vs-target.md` | T2 | LEGACY_BASELINE + TARGET_REGRESSION |
| 03 | `03-must-preservation.md` | T3 | Auto MUST start (not MAY) |
| 04 | `04-must-not-preservation.md` | T4 | MUST NOT force start preserved |
| 05 | `05-continue-ff-equivalence.md` | T5 | continue ≡ ff tasks |
| 06 | `06-regression-auto-shelf-sample.md` | real sample | generator must not emit known bad shapes |

## Non-goals

- Do not edit product `openspec/changes/auto-shelf-exhausted-pause-retest/**`
  as part of applying this fixture pack.
- Do not change `/opsx-new`, owner-contract-review, scenario-coverage,
  apply/verify/archive in these fixtures.
