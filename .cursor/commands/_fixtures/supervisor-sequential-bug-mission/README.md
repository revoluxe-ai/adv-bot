# Fixtures: /opsx-supervisor BUG_MISSION sequential

Process-only dry-run cases for deterministic multi-finding orchestration.

Command under test: `/opsx-supervisor` (BUG_MISSION mode)
Schemas: `contracts/bug-episode/ROUTE_TRANSITION.md`, `SUPERVISOR_POLICY.md`

## How to use

Given durable envelopes in each fixture, a correct supervisor reducer MUST
emit the stated `Expected` recovery / next dispatch / mission fields.
No production writes. No LLM route invention.

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-route-a-single.md` | T1 Route A full chain | claim→classify→RED→fix→GREEN→CLOSED; no planner |
| 02 | `02-two-sequential.md` | T2+T4 | ROOT-001 terminal before ROOT-002 ACTIVE |
| 03 | `03-worker-pass-not-mission.md` | T3 | classify PASS ⇒ MISSION_COMPLETE=no |
| 04 | `04-all-terminal-mission-complete.md` | T5 | MISSION_COMPLETE=yes only after all-terminal proof |
| 05 | `05-blocked-stops-mission.md` | T6 | BLOCKED ⇒ ROOT-002 never starts |
| 06 | `06-needs-owner-stops.md` | T7 | NEEDS_OWNER ⇒ stop_mission |
| 07 | `07-route-contract-conflict.md` | T8 | contradictory next vs precondition ⇒ PAUSED |
| 08 | `08-envelope-wrong-finding.md` | T9 | ENVELOPE_INTEGRITY_FAIL |
| 09 | `09-stale-claim.md` | T10 | no writer dispatch |
| 10 | `10-resume-after-classify.md` | T11 | no re-classify; next from durable |
| 11 | `11-execution-outcome-unknown.md` | T12 | PAUSED EXECUTION_OUTCOME_UNKNOWN |
| 12 | `12-false-positive-advance.md` | T13 | FP terminal → next finding; no fix |
| 13 | `13-route-b.md` | T14 | NEXT=/opsx-update not hardcoded Route A |
| 14 | `14-deterministic-replay.md` | T15 | same state+envelopes ⇒ same NEXT |
| 15 | `15-planfit-regression.md` | SUP-ASEP-FULL-ENV-002 | structural classify; no mission complete; GO_TOKEN=FORBIDDEN |
| 16 | `16-top-level-timeout-defaults.md` | SUP-DEF-001 | empty clocks forbidden; §12.0 defaults mandatory |
| 17 | `17-task-abort-execution-outcome-unknown.md` | SUP-DEF-002 | Task abort → PAUSED EXECUTION_OUTCOME_UNKNOWN |
| 18 | `18-green-prose-without-path-rejected.md` | SUP-DEF-003 | prose GREEN without path → REJECTED |
| 19 | `19-three-sequential-workers.md` | SUP-LIVE-001 | 3 workers success → TERMINAL_RESULT→ADVANCE→DISPATCH |
| 20 | `20-completed-worker-not-running.md` | SUP-LIVE-002 | accepted worker MUST leave RUNNING |
| 21 | `21-id-correlation-mismatch.md` | SUP-LIVE-003 | optional IDs absent OK; handle mismatch → PAUSED |
| 22 | `22-reconciliation-no-graph-mutation.md` | SUP-LIVE-004 | unchanged fingerprint cannot reconcile/route loop |
| 23 | `23-no-active-worker-dispatch-or-block.md` | SUP-LIVE-005 | unfinished + no active worker → dispatch or block |
| 24 | `24-repeated-state-no-progress.md` | SUP-LIVE-006 | identical state → SUPERVISOR_NO_PROGRESS |
| 25 | `25-manual-abort-after-progress.md` | SUP-LIVE-007 | abort ≠ explanation of prior NO_PROGRESS |

## Static matrix

| Rule | Fixtures |
|------|----------|
| sequential max_active=1 | 01, 02, 05 |
| PASS ≠ mission complete | 03, 15 |
| all-terminal proof | 04 |
| stop on blocked/needs_owner | 05, 06 |
| ROUTE_CONTRACT_CONFLICT | 07 |
| ENVELOPE_INTEGRITY_FAIL | 08 |
| claim gate | 09 |
| resume | 10, 14 |
| EXECUTION_OUTCOME_UNKNOWN | 11, 17 |
| Route C / B | 12, 13 |
| policy ≠ route semantics | 13, 14 |
| top-level timeout defaults | 16 |
| platform Task abort | 17 |
| durable GREEN evidence gate | 18 |
| sequential 3-worker progress | 19 |
| completed worker not RUNNING | 20 |
| handle correlation (optional IDs) | 21 |
| reconcile loop guard | 22 |
| no-active-worker dispatch-or-block | 23 |
| SUPERVISOR_NO_PROGRESS | 24 |
| abort vs prior no-progress | 25 |
