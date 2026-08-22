# Corrective V7 Report — Uncommitted Worktree Control Model

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V7_IMPLEMENTED
COMMAND: /opsx-bug-team
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
REAL_BUG_EXECUTION_ALLOWED: NO
COMMIT_ALLOWED: NO
INDEPENDENT_TESTER_PASS: NOT_ISSUED
```

Evidence:

```text
.tmp/opsx-bug-team-harness/corrective-v7/20260728T065536Z/
```

## Control-model change

Owner controlling decision applied:

```text
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
COMMAND_BEHAVIOR: RUN_TO_TERMINAL_RESULT
INTERMEDIATE_OWNER_PRODUCTION_GATE: REMOVED_FOR_CONTROLLED_LIVE_UNCOMMITTED
INTERMEDIATE_OWNER_CLOSURE_GATE: REMOVED
COMMIT_AUTHORITY: USER_ONLY
```

Default live mode after future activation: `CONTROLLED_LIVE_UNCOMMITTED`.

Legacy `OWNER_GATED` preserves previous Owner production GO + Owner final closure GO.

## Automatic local execution rules

After `RED_CONFIRMED`, host validates:

```text
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
RED_STATUS / RED_PACKET / FROZEN_HASHES / ROUTE / WRITE_BOUNDARY
EXTERNAL_MUTATION_REQUIRED: NO
```

If valid → `LOCAL_IMPLEMENTATION_AUTHORIZED: YES` → IMPLEMENTATION_EXECUTOR (no `WAITING_OWNER`).

After FANIN `READY_FOR_CLOSURE` + `BLOCKING_FINDINGS: NONE` → auto CLOSURE_OPERATOR (no `WAITING_OWNER_FINAL_CLOSURE`).

Module: `runtime/control_model.py` (wired from `live_task_hop.prepare_live_hop`).

## Forbidden external operations

Rejected by `reject_forbidden_shell_command` / local authority:

```text
git commit / git push / git add / gh pr create
kubectl apply|delete / helm / terraform apply
deploy / production DB writes / billing / secret rotation / customer data
```

Terminal status never claims `READY_TO_DEPLOY` / `DEPLOYED` / `COMMITTED` / `PUSHED`.

Final user control:

```text
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
COMMIT_CREATED: NO
```

## End-to-end Route A/B/C/D (controlled)

| ID | Result |
|----|--------|
| V7-FLOW-01 Route A | PASS — RED → local executor → GREEN → hunt → fan-in → closure |
| V7-FLOW-02 Route B CHANGED | PASS — TASK_DELTA → update → RED → apply → closure |
| V7-FLOW-03 Route B UNCHANGED | PASS — RED → fix → GREEN → closure |
| V7-FLOW-04 Route C | PASS — closed without implementation |
| V7-FLOW-05 Route D | PASS — durable handoff, no fake closure |
| V7-FLOW-06 insufficient | PASS — blocked, no implementation |

## Human summary

- Artifact: `results/HUMAN_SUMMARY.md` (proof: `<PROOF_ROOT>/case/results/HUMAN_SUMMARY.md`)
- Chat section: `ПРОСТОЕ ОБЪЯСНЕНИЕ` (12 plain-language questions)
- Writer: `CLOSURE_OPERATOR` only (FAN_IN still `FANIN.md` only)
- Example: evidence `human-example/case/results/HUMAN_SUMMARY.md`

## Uncommitted-worktree state

Successful episode leaves local file changes for user review. Builder does not commit.
Unrelated dirty files separated via `classify_worktree_changes`.

## V7 tests

```text
command: python .cursor/pipeline/bug-team/harness/run_corrective_v7_tests.py
total: 26
passed: 26
failed: 0
```

Gate / user / human matrix: V7-GATE-01..06, V7-USER-01..05, V7-HUMAN-01..08, V7-FS-CLOSURE.

## V6/V5/V4/V3/V2 regressions

| Suite | Total | Passed | Failed |
|-------|-------|--------|--------|
| V6 | 31 | 31 | 0 |
| V5 | 39 | 39 | 0 |
| V4 | 29 | 29 | 0 |
| V3 | 34 | 34 | 0 |
| V2 | 18 | 18 | 0 |

Not weakened: packet authority, idempotency, retry registry, stale-output rejection, write boundaries, NOT_ACTIVE, route trace, timeout safety. `REVIEW_PROOF_ONLY` still requires Owner production GO.

## Candidate hashes (after V7)

See `hashes/CANDIDATE_HASHES.json` in evidence. Notable:

| Path | Role |
|------|------|
| `runtime/control_model.py` | **new** — local authority, auto-closure, HUMAN_SUMMARY |
| `runtime/live_task_hop.py` | uncommitted path skips Owner GO when authorized |
| `runtime/activation.py` | CONTROLLED_LIVE_UNCOMMITTED proof / future ACTIVE |
| `runtime/fs_boundary.py` | executor local paths + CLOSURE HUMAN_SUMMARY |
| `harness/run_corrective_v7_tests.py` | **new** |

## Product isolation

```text
PRODUCT_APP_FILES_CHANGED: NONE
PRODUCT_TEST_FILES_CHANGED: NONE
OPENSPEC_PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CREATED: NONE
RUNTIME_ACTIVATED: NO
COMMIT_CREATED_BY_CORRECTIVE_BUILDER: NO
```

## Activation status

```text
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
FUTURE_ACTIVATION_CONTRACT:
  ACTIVATION_MODE: CONTROLLED_LIVE_UNCOMMITTED
  OWNER_PRODUCTION_GATE: NOT_REQUIRED_FOR_LOCAL_WORKTREE_WRITES
  OWNER_CLOSURE_GATE: NOT_REQUIRED
  COMMIT_AUTHORITY: USER_ONLY
  EXTERNAL_MUTATIONS: FORBIDDEN
```

Do **not** reuse old activation receipt requiring Owner production/closure gates.

## ONE_NEXT_ACTION

```text
Targeted Independent Control-Model Test
```
