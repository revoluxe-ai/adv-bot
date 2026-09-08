# FANIN.md assemble contract

Policy SoT: `.cursor/pipeline/ORCHESTRATION_MVP.md` §5.

## Path

```text
.opsx/runs/bug-cases/<ROOT_CASE_ID>/results/FANIN.md
```

## Assembler write boundary

```text
PRODUCTION_READ_ONLY: YES
COMMAND_AND_GRAPH_READ_ONLY: YES
CASE_MAP_WRITE_ALLOWED:
  .opsx/runs/bug-cases/<ROOT_CASE_ID>/results/FANIN.md
ALL_OTHER_WRITES: DENIED
Mechanism: /opsx-materialize-bug-queue mode=fanin_assemble
NEW_SLASH: /opsx-fan-in-* FORBIDDEN
Owner authority: NONE
```

## Preconditions (assemble forbidden until)

```text
ROOT_CASE_ID present
ROOT_FINDING_ID / ROOT_INVARIANT known
HUNT_PASSES_EXECUTED ≤ MAX_HUNT_PASSES
BRANCH_REGISTRY complete for all started branches
every started branch has EPISODE_TERMINAL ∈ episode terminal set
LIMITS_CHECK evaluated
```

## Output required fields

```text
STATUS: FANIN_READY | FANIN_INCOMPLETE
ROOT_BUG:
ROOT_CAUSE_PATTERN:
ERROR_CLASS:
SIBLING_VARIANTS:
FIX_PATTERNS:
REGRESSION_TEST_PATTERN:
PREVENTION_RULE_CANDIDATE:
REUSABLE_CHECK_CANDIDATE:
REMAINING_EXCEPTIONS:
BRANCH_SUMMARY:
REGRESSION_STATUS:
LIMITS_CHECK:
CHECKS:
  1_FIXED_HAVE_RED_GREEN_GO: PASS|FAIL|N/A
  2_NO_WEAKEN: PASS|FAIL|N/A
  3_NO_DOUBLE_FIX: PASS|FAIL
  4_NO_CONFLICTING_PRODUCTION_DIFFS: PASS|FAIL|N/A
  5_ONE_ROOT_INVARIANT_OR_EXPLICIT_OUTEPISODE: PASS|FAIL
  6_LIMITS_NOT_EXCEEDED: PASS|FAIL
```

## FANIN_READY

```text
FANIN_READY
  iff assembly complete
  ∧ all started branches terminal
  ∧ checks 3–6 PASS
  ∧ checks 1–2 PASS or N/A with Owner-noted exceptions
  ∧ NO_OPEN_SAME_INVARIANT_CANDIDATES (HARD_BLOCK_READY)
```

Otherwise `FANIN_INCOMPLETE`.

### HARD_BLOCK_READY — open SAME_INVARIANT candidates

Hunt / residual candidates with:

```text
RELATION_TO_ROOT_CANDIDATE = SAME_INVARIANT_FINDING
STATUS ∈ {open_candidate, OPEN_CANDIDATE}
```

that are **not** durably disposed as `FALSE_POSITIVE` or `OUT_OF_SCOPE`
**MUST** block episode readiness.

When any such candidate exists:

```text
STATUS: FANIN_INCOMPLETE
BLOCKING_FINDINGS: include each HUNT_CANDIDATE_ID / PROPOSED_FINDING_ID
CLOSURE_READINESS: MUST NOT be READY_FOR_CLOSURE
BLOCKING_FINDINGS=NONE: FORBIDDEN
BLOCKS_ROOT_CLOSURE=false for SAME_INVARIANT open candidates: FORBIDDEN
```

Required pasteable next (in FANIN / INDEX recovery):

```text
/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
```

(or materialize sibling finding, then fanout). Listing the residual only under
`REMAINING_EXCEPTIONS` / `may_need_family_fanout` while claiming
`FANIN_READY` / `READY_FOR_CLOSURE` is Forbidden.

Allowed path to `FANIN_READY` after such a candidate appears:

1. materialize + terminate the SAME_INVARIANT branch, **or**
2. durable `FALSE_POSITIVE` / `OUT_OF_SCOPE` disposition record.

```text
LEARNING_READY ≠ FANIN_READY
```

Fanout `LEARNING_READY` must never be treated as episode fan-in complete.
