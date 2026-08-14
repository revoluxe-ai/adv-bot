# Fixtures: /opsx-owner-contract-review

Process-only regression cases for independent Owner Contract semantic review.

Command under test: `/opsx-owner-contract-review`

## How to use

Dry-run: given the fixture’s durable inputs, a correct reviewer MUST emit the
`Expected` check outcomes and `REVIEW_STATE` (and `VERDICT` alias where
stated).

These fixtures do **not** authorize writes. They do **not** hard-gate
`continue` / `ff`.

Cross-contract: Fixture 10 handoff shape MUST be accepted by
`/opsx-new` REPAIR MODE without human rewrite — see sibling directory
`../opsx-new-owner-contract-repair/`.

## Index

| ID | File | Primary check / theme | Expected REVIEW_STATE |
|----|------|-----------------------|------------------------|
| 01 | `01-wrong-technical-reinterpretation.md` | INTENT_PRESERVATION | FAIL or READY_FOR_REPAIR (known wrong meaning) |
| 02 | `02-agent-proposal-promoted.md` | OWNER_DECISION_PROVENANCE | READY_FOR_REPAIR \| NEEDS_OWNER (not PASS) |
| 03 | `03-ambiguous-terminology.md` | TERMINOLOGY | NEEDS_OWNER (or FAIL if term contradicted) |
| 04 | `04-contradictory-start-semantics.md` | INTERNAL_CONSISTENCY | NEEDS_OWNER \| READY_FOR_REPAIR |
| 05 | `05-stale-correction.md` | STALE_ASSUMPTIONS | READY_FOR_REPAIR; OWNER_INPUT_REQUIRED NO |
| 06 | `06-clean-auto-shelf-exhausted-pause-retest.md` | all | PASS only with durable provenance |
| 07 | `07-needs-context-missing-handoff.md` | T1 missing handoff | NEEDS_CONTEXT (not FAIL) |
| 08 | `08-needs-owner-epoch-choice.md` | T2 / Finding B | NEEDS_OWNER |
| 09 | `09-stale-writer-auto-restart.md` | T3 / Finding A | READY_FOR_REPAIR; OWNER_INPUT_REQUIRED NO |
| 10 | `10-ready-for-repair-handoff.md` | T4 handoff literal | READY_FOR_REPAIR + pasteable `/opsx-new` + OWNER_REVIEW_HANDOFF |
| 11 | `11-pass-after-repair.md` | T9 repaired | PASS |
| 12 | `12-writer-regression.md` | T10 regression | not PASS; bounded new cycle |

## Static matrix

| Check / rule | Fixture coverage |
|--------------|------------------|
| INTENT_PRESERVATION | 01, 06 |
| OWNER_DECISION_PROVENANCE | 02, 06, 10 |
| INTERNAL_CONSISTENCY | 04, 06, 09 |
| TERMINOLOGY | 03, 06 |
| SCOPE_INTEGRITY | 01, 06 |
| ACCEPTANCE_COHERENCE | 04, 06, 09 |
| STALE_ASSUMPTIONS | 05, 09 |
| CONTRACT_VS_REALITY | optional / NOT_CHECKED unless stated |
| REVIEW_STATE NEEDS_CONTEXT | 07 |
| REVIEW_STATE NEEDS_OWNER | 03, 08, 04 (no durable proof) |
| REVIEW_STATE READY_FOR_REPAIR | 05, 09, 10, 04 (with durable proof) |
| REVIEW_STATE PASS | 06, 11 |
| OWNER_REVIEW_HANDOFF MODE REPAIR_EXISTING_OWNER_CONTRACT | 10 |
| pasteable `/opsx-new` + handoff (no Owner rewrite) | 10 |
| OWNER_INPUT_REQUIRED NO for proven writer defects | 05, 09 |
| Re-review / writer regression | 11, 12 |
| MODE READ_ONLY / FILES_CHANGED none | all |
| continue/ff/apply/verify/Supervisor untouched by this command’s writes | n/a (out of fixture scope; meta-design invariant) |

## Ideal interactive transcript (normative sketch)

```text
/opsx-owner-contract-review change=X
→ REVIEW_STATE: NEEDS_CONTEXT  (ask EVOLUTION_HANDOFF)

Owner pastes handoff
→ REVIEW_STATE: NEEDS_OWNER    (one real product question)

Owner answers
→ REVIEW_STATE: READY_FOR_REPAIR
  UX: "Скопируйте блок ниже в новый/Writer чат:"
  pasteable:
    /opsx-new
    OWNER_REVIEW_HANDOFF
    MODE: REPAIR_EXISTING_OWNER_CONTRACT
    ...

Owner pastes block into writer chat unchanged
→ /opsx-new REPAIR MODE applies only owner-contract.md
→ /opsx-owner-contract-review change=X
→ REVIEW_STATE: PASS
  MODE: READ_ONLY
  FILES_CHANGED: none
```
