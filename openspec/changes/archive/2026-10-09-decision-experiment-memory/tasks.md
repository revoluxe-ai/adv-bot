# Tasks: decision-experiment-memory (foundation archive)

FOUNDATION_SCOPE: **SLICE_A_ONLY**
OWNER_SCOPE_DECISION: **OPTION_A_FOUNDATION_ONLY**
STAGE_MERGE: `5c2e15a5805d2a048fd339b173f19c249d3a3353` (PR #460)
SLICE_A_HEAD: `20248943cee6e785e4554ddad23ba6c0cd224144`

## 1. Planning gate

- [x] 1.1 Initial planning package.
- [x] 1.2 Methodology addendum repair.
- [x] 1.2b Final architecture locks.
- [x] 1.3 Owner contract review — architecture accepted.
- [x] 1.4 Scenario coverage plan + receipt (`scenario-coverage/`).
- [x] 1.5 Spec repair: INVALID/INCONCLUSIVE mapping, `experiment_design`, abort projection.
- [x] 1.6 Planning review — `PLANNING_REVIEW.md` PASS (foundation archive scope, 2026-10-09).
- [x] 1.7 ADL promoted to `openspec/decisions/decision-experiment-memory-ownership/`.

## 2. Slice A — domain foundation (DELIVERED)

- [x] 2.1 Domain types + refs (`ApplyEvidenceRef`, `DryRunReceiptRef`, …).
- [x] 2.2 Event taxonomy + projection rules (vocabulary).
- [x] 2.3 Ports + test-only `InMemoryDecisionMemoryRepository`.
- [x] 2.4 Unit tests (`tests/unit/decision_experiment_memory/`).
- [x] 2.5 Vocabulary freeze — `SLICE-A-VOCABULARY-FREEZE.md`.

## 3–7. Future changes (NOT DELIVERED — boundaries recorded)

- [x] 3.0 `decision-memory-persistence` — recorded in `openspec/evolution/decision-experiment-memory-future-boundaries.md`
- [x] 4.0 `decision-memory-exposure-ingest` — recorded (not implemented)
- [x] 5.0 `decision-memory-evaluator` — recorded (not implemented)
- [x] 6.0 `decision-memory-posthoc` runtime — recorded (not implemented)
- [x] 7.0 `decision-memory-ai-package` export — recorded (not implemented)

## Archive close

- [x] A.1 Reconcile proposal/contract/design/spec to foundation truth
- [x] A.2 `FOUNDATION_CERTIFICATION.md` + scenario evidence
- [x] A.3 Permanent ADR verified (`decision-experiment-memory-ownership`)
- [x] A.4 `openspec archive decision-experiment-memory` + post-archive verify

## Verification

- [x] 8.1 `openspec validate decision-experiment-memory --strict`
- [x] 8.2 Slice A unit tests + adjacent Apply ref unit tests
