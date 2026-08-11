# Fixtures: Design Generation Readiness

Process-only regression for:

```text
upstream owner-contract / specs / decisions + repo evidence
  → DESIGN_READINESS
  → design.md  (/opsx-continue ≡ /opsx-ff)
```

Commands under test:

- `/opsx-continue` / `/opsx-ff` (when artifact is `design`)
- contract: `.cursor/pipeline/contracts/DESIGN_GENERATION.md`

## Authority invariant

```text
DESIGN MUST RESOLVE ARCHITECTURE BEFORE IMPLEMENTATION
same upstream context → semantically equivalent design
MUST/MUST NOT modality preserved
READY + apply-time architecture = FORBIDDEN
```

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-unresolved-durable-sot.md` | T1 | BLOCKED TECHNICAL_DESIGN_UNRESOLVED |
| 02 | `02-resolvable-technical-choice.md` | T2 | READY + chosen SoT/owner/write/rationale |
| 03 | `03-must-preservation.md` | T3 | Auto MUST start (not MAY) |
| 04 | `04-must-not-preservation.md` | T4 | MUST NOT force-start preserved |
| 05 | `05-upstream-normative-conflict.md` | T5 | BLOCKED UPSTREAM_NORMATIVE_CONFLICT |
| 06 | `06-implementation-critical-open-question.md` | T6 | readiness FAIL / BLOCKED |
| 07 | `07-harmless-naming-open-question.md` | T7 | READY allowed |
| 08 | `08-continue-ff-equivalence.md` | T8 | continue ≡ ff design rules |
| 09 | `09-regression-auto-shelf-sample.md` | R9 | forbid known bad generator shapes |

## Non-goals

- Do not edit product `openspec/changes/auto-shelf-exhausted-pause-retest/**`
  as part of applying this fixture pack.
- Do not change `/opsx-new`, owner-contract-review, scenario-coverage,
  tasks generation, apply/verify/archive in these fixtures.
