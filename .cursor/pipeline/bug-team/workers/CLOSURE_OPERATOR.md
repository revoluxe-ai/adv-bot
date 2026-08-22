# Worker: CLOSURE_OPERATOR

```text
WORKER_ID: CLOSURE_OPERATOR
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
SUBAGENT_EXECUTION_REQUIRED: YES
TASK_SUBAGENT_TYPE: generalPurpose
MODEL_SELECTION_POLICY: auto
```

## INPUT_PACKET_SCHEMA

```text
Default CONTROLLED_LIVE_UNCOMMITTED:
  WORKER_IO
  + FANIN (READY_FOR_CLOSURE, BLOCKING_FINDINGS=NONE)
  + validated LEARNING_DECISION.json
    (LEARNING_STAGE_INVOKED=true, LEARNING_STATUS=COMPLETE,
     LEARNING_VERDICT in closure-allowed set,
     PROMOTION_DECISION in {NONE|DEFERRED|RESOLVED_NO_PROMOTE|QUEUED})
  → automatic dispatch (no Owner closure stop)

Legacy OWNER_GATED:
  WORKER_IO + FANIN + OWNER_FINAL_CLOSURE_DECISION
```

## HARD_BLOCK_READY gate (mandatory)

Reject closure when FANIN / case map still has an open SAME_INVARIANT hunt
candidate (`STATUS ∈ {open_candidate, OPEN_CANDIDATE}`, not durably
`FALSE_POSITIVE` / `OUT_OF_SCOPE`). Required rejection status:

```text
BLOCKED_OPEN_SAME_INVARIANT_CANDIDATE
```

`BLOCKS_ROOT_CLOSURE=false` on such a residual MUST NOT authorize closure.
Pasteable recovery: `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`.
Authority: `.cursor/pipeline/contracts/bug-episode/FANIN.md` HARD_BLOCK_READY.

When closing (or when residuals were cleared this hop), INDEX recovery row
MUST list any remaining OPEN_CANDIDATE debt or clear BLOCKERS accordingly
(see `/opsx-materialize-bug-queue` INDEX rules).

## Learning gate (mandatory)

Reject closure unless learning decision validates. Required rejection statuses:

```text
BLOCKED_LEARNING_DECISION_MISSING
BLOCKED_LEARNING_DECISION_INVALID
BLOCKED_LEARNING_INCOMPLETE
BLOCKED_OWNER_LEARNING_DECISION_REQUIRED
```

Closure must not require actual promotion. Candidate verdicts may close only
with `PROMOTION_DECISION` ∈ {`DEFERRED`, `RESOLVED_NO_PROMOTE`, `QUEUED`}.

Live predecessor: `FAMILY_LEARNING_WORKER` (not direct fan-in).

## OUTPUT / WRITE_BOUNDARY

```text
ALLOWED:
  results/OWNER-CLOSURE-<FINDING_ID>.md
  results/HUMAN_SUMMARY.md
  CASE.md terminal update
  LEDGER.md terminal update
  finding terminal update
  ROUTE-TRACE.jsonl closure events
  INDEX.md corresponding case update
FORBIDDEN:
  results/FANIN.md (Fan-In only)
  creating LEARNING_DECISION (learning worker only)
  git commit / push / deploy claims
  activating global rules / superclass
```

## TERMINAL

```text
CASE_STATUS: CLOSED
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED: NO
USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT
```

Must produce plain-language `HUMAN_SUMMARY.md`.
