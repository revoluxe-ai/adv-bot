# OPSX bug-episode orchestration MVP (live process contract)

```text
STATUS: LIVE_PROCESS_CONTRACT
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
CANDIDATE_WORKTREE_BEHAVIOR_CHANGED: YES
LIVE_WORKSPACE_BEHAVIOR_CHANGED: YES
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
ACTIVATION_SOURCE_COMMIT: bcd132ccf62712f6dd0d00a18a0c26f7dc8c8179
INDEPENDENT_TEST_RESULT: T1–T18 PASS
TARGETED_RETEST_RESULT: PASS
```

## Document role

This file is a **shared process contract** for product/logic bug episodes.

It is **not**:

- a live command;
- a slash `/opsx-fan-in-*` command;
- an authority override of `/opsx-verify`, `/opsx-archive`, `/opsx-commit`,
  or command GO gates;
- a replacement for `.cursor/pipeline/GRAPH.md` (GRAPH remains
  `navigation_snapshot_only`; navigation advice never overrides command
  gates, Owner authority, or durable case state).

**Live activation:** Owner issued `GO_ACTIVATE`. Companion command/schema
contracts from the tested candidate are merged into the live workspace and
are authoritative for live OPSX orchestration of product/logic bug episodes.

```text
ACTIVATION_SOURCE_COMMIT: bcd132ccf62712f6dd0d00a18a0c26f7dc8c8179
INDEPENDENT_TEST_RESULT: T1–T18 PASS
TARGETED_RETEST_RESULT: PASS
```

**Dual-truth:** prior draft/candidate wording is superseded by this live
contract and the activated companion command texts.

---

## Scope

**In scope:** product / behavioral bug episodes that may:

1. require a regression proof before production repair;
2. expand via root-aware invariant sibling hunt;
3. promote a **class-level** process lesson after all started branches terminate.

**Out of scope:**

- typing-only packets (`/opsx-fix-types`, static-check);
- process / command-contract defects
  (`/opsx-meta-fix-command-defects`,
  `/opsx-admin-command-promote-process-lesson`);
- OpenSpec change apply/verify/archive lifecycle (except optional later GRAPH
  navigation edges);
- `/opsx-static-check` fan-in (different domain).

---

## Live OPSX bug episode sequence

### Canonical pre-implementation routing (mandatory)

```text
BUG SIGNAL
  → /opsx-materialize-bug-queue (durable intake / findings)
  → /opsx-claim-next-bug          # when claimable queue
  → /opsx-classify-bug            # mandatory before implementation route
  → Route A | B | C | D
```

`/opsx-classify-bug` is **required** before choosing `/opsx-fix-bug`,
`/opsx-update`, `/opsx-apply`, or terminal close. Skipping classify when a
durable finding is claimed/available for adjudication is a hard process
blocker (`blocked_needs_classify_first`).

### Route A — implementation bug

```text
CLASSIFICATION: IMPLEMENTATION_BUG
  (classify label: implementation_bug)

→ /opsx-fix-bug WITHOUT GO
→ BUG_CONFIRMED + verdict fix_now
→ /opsx-test (author + run RED; no production GO)
→ RED_CONFIRMED | fail-states | BUG_NOT_TESTABLE → Owner exception
→ OWNER_PRODUCTION_GO (exact token GO) only if §1.2 holds
→ /opsx-fix-bug GO  (production only; test freeze by default)
→ /opsx-test verify → GREEN_CONFIRMED
```

Classify seed state for the first hop: `CURRENT_ROUTE_STATE=AWAITING_FIX_BUG`
with machine `ROUTE_TRANSITION.PRECONDITIONS.GO_TOKEN=FORBIDDEN` (see
`contracts/bug-episode/ROUTE_TRANSITION.md`). That is **not** the same
token as post-`TASK_DELTA` `AWAITING_FIX_BUG_RED`. Supervisor must consume
the structured transition; prose «no GO until RED» does not replace
`NEXT_COMMAND=/opsx-fix-bug` with `/opsx-test`.

### Route B — specification defect or gap

```text
CLASSIFICATION: SPEC_BUG | SPEC_GAP
  (classify labels: spec_bug | implementation_bug_with_spec_gap)

CHOSEN_ROUTE: ROUTE_B
EXPECTED_NEXT_COMMAND: /opsx-update
EXPECTED_EXECUTION_ROUTE: PENDING_UNTIL_TASK_DELTA
ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
CURRENT_ROUTE_STATE: AWAITING_SPEC_UPDATE

→ /opsx-update <change-id>   # immediate process step; NOT production GO
→ specification corrected
→ TASK_DELTA_CHECK (§0.2)
```

Route B layers (do not collapse):

```text
CLASSIFICATION ROUTE:           ROUTE_B
IMMEDIATE PROCESS STEP:         /opsx-update
IMPLEMENTATION EXECUTION ROUTE: PENDING_UNTIL_TASK_DELTA
  (chosen only after TASK_DELTA)
```

`/opsx-update` MUST NEVER be stored as `EXPECTED_EXECUTION_ROUTE` or
`ACTUAL_EXECUTION_ROUTE`.

After `/opsx-update`:

```text
TASK_DELTA: CHANGED
  → EXPECTED_EXECUTION_ROUTE: /opsx-apply
  → EXPECTED_NEXT_COMMAND: /opsx-apply
  → CURRENT_ROUTE_STATE: AWAITING_APPLY_RED

TASK_DELTA: UNCHANGED
  → EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
  → EXPECTED_NEXT_COMMAND: /opsx-fix-bug
  → CURRENT_ROUTE_STATE: AWAITING_FIX_BUG_RED

ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
```

(Legacy readers may map YES→CHANGED, NO→UNCHANGED; new writes use only
CHANGED|UNCHANGED.)

Then both executors follow the same RED → Owner GO → GREEN path as Route A
(§1). `/opsx-update` does **not** replace the implementation executor.
New/changed tasks do **not** auto-authorize `/opsx-apply` production edits.
Executor start must set `ACTUAL_EXECUTION_ROUTE` and reconcile (§0.5).

### Route C — false positive

```text
CLASSIFICATION: FALSE_POSITIVE
  (classify label: false_positive)

→ REJECTED / CLOSED_NO_IMPLEMENTATION
EXPECTED_EXECUTION_ROUTE: CLOSED_NO_IMPLEMENTATION
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
```

### Route D — out of scope

```text
CLASSIFICATION: OUT_OF_SCOPE
  (classify label: out_of_scope)

→ ROUTE_TO_OTHER_PROCESS
EXPECTED_EXECUTION_ROUTE: ROUTE_TO_OTHER_PROCESS
ROUTE_TARGET_PROCESS_ID: <required>
ROUTE_TARGET_REASON: <required>
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
```

Missing `ROUTE_TARGET_PROCESS_ID` → `BLOCKED_MISSING_ROUTE_TARGET`.
Not opportunistic fix inside current episode.

### Post-fix episode expansion (unchanged shape)

```text
→ optional bounded invariant hunt / fan-out children
→ per-branch: classify (if new finding) → route → RED → Owner GO → GREEN → terminal
→ ALL started branches terminal
→ assemble FANIN.md (materialize mode=fanin_assemble; no /opsx-fan-in-*)
→ FANIN_READY
→ /opsx-learn-from-bug with FANIN_PATH=…  (class-level)
→ Owner FINAL class verdict
```

Finding-scoped notes without class promotion may skip FANIN; they must not
claim a confirmed class lesson or class-rule GO write.

Every significant hop appends to durable `ROUTE-TRACE.jsonl` (§0.3).

---

## 0. Classify-first, task delta, route trace

### 0.1 Classify-first gate

Before `/opsx-fix-bug` adjudication that selects an implementation route,
or before `/opsx-apply` / `/opsx-update` on a claimed finding in a bug
episode, durable route state MUST record a classification:

```text
CURRENT_CLASSIFICATION ∈
  IMPLEMENTATION_BUG | SPEC_BUG | SPEC_GAP | FALSE_POSITIVE | OUT_OF_SCOPE
```

Produced by `/opsx-classify-bug` and mirrored in `LEDGER.md` →
`## ROUTE_STATE`.

For Route B (`SPEC_BUG` | `SPEC_GAP`) the classify receipt MUST also record:

```text
CHOSEN_ROUTE: ROUTE_B
EXPECTED_NEXT_COMMAND: /opsx-update
EXPECTED_EXECUTION_ROUTE: PENDING_UNTIL_TASK_DELTA
CURRENT_ROUTE_STATE: AWAITING_SPEC_UPDATE
```

`/opsx-update` gates on those handoff fields (not on
`EXPECTED_EXECUTION_ROUTE=/opsx-update`). Missing `CHOSEN_ROUTE` with only
`SPEC_BUG`/`SPEC_GAP` is incomplete — do not silently infer Route B.

If classification is missing → blocker `blocked_needs_classify_first`;
pasteable next:

```text
/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
```

### 0.2 TASK_DELTA after `/opsx-update`

Schema: `.cursor/pipeline/contracts/bug-episode/TASK_DELTA.md`.

Canonical durable decision:

```text
TASK_DELTA: CHANGED | UNCHANGED
EXPECTED_EXECUTION_ROUTE: /opsx-apply | /opsx-fix-bug
EXPECTED_NEXT_COMMAND: /opsx-apply | /opsx-fix-bug
TASK_DELTA_EVIDENCE_PATH
```

Rule:

```text
CHANGED   → EXPECTED_EXECUTION_ROUTE=/opsx-apply
            EXPECTED_NEXT_COMMAND=/opsx-apply
            CURRENT_ROUTE_STATE=AWAITING_APPLY_RED
UNCHANGED → EXPECTED_EXECUTION_ROUTE=/opsx-fix-bug
            EXPECTED_NEXT_COMMAND=/opsx-fix-bug
            CURRENT_ROUTE_STATE=AWAITING_FIX_BUG_RED
```

Seed reconciliation:

```text
ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
ACTUAL_NEXT_COMMAND: PENDING
NEXT_COMMAND_RECONCILIATION: PENDING
```

Before TASK_DELTA (post-classify Route B only):

```text
EXPECTED_EXECUTION_ROUTE: PENDING_UNTIL_TASK_DELTA
EXPECTED_NEXT_COMMAND: /opsx-update
CURRENT_ROUTE_STATE: AWAITING_SPEC_UPDATE
```

### 0.3 Durable team route trace

Schema: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md` (`SCHEMA_VERSION: 2`).

```text
RUNTIME:
  .tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Append-only. Monotonic `EVENT_SEQUENCE` per CASE_ID; unique `EVENT_ID`;
`PREVIOUS_EVENT_ID` except first event.

Every producer event MUST record at least:

```text
EVENT_ID EVENT_SEQUENCE CASE_ID FINDING_ID EVENT_TYPE COMMAND
ACTOR_ROLE ACTOR_AGENT_ID ACTOR_CHAT_ID
FROM_STATE TO_STATE STARTED_AT TERMINAL_STATUS
```

Route-selecting / executing hops also record:

```text
CHOSEN_ROUTE
EXPECTED_NEXT_COMMAND
ACTUAL_NEXT_COMMAND
NEXT_COMMAND_RECONCILIATION
EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION
```

Analytics MUST distinguish:

```text
CHOSEN_ROUTE            = high-level Route A|B|C|D
EXPECTED_NEXT_COMMAND   = immediate process handoff
EXPECTED_EXECUTION_ROUTE= eventual production executor
```

### 0.4 Human-readable `## ROUTE_STATE` (LEDGER)

In `.tmp/opsx-bug-cases/<CASE_ID>/LEDGER.md` maintain **current** snapshot
aligned with the latest applicable JSONL event:

```text
## ROUTE_STATE

CURRENT_CLASSIFICATION:
CHOSEN_ROUTE:
EXPECTED_NEXT_COMMAND:
ACTUAL_NEXT_COMMAND:
NEXT_COMMAND_RECONCILIATION:
EXPECTED_EXECUTION_ROUTE:
ACTUAL_EXECUTION_ROUTE:
ROUTE_RECONCILIATION:

CURRENT_ROUTE_STATE:
LAST_ROUTE_EVENT_ID:
LAST_ROUTE_EVENT_SEQUENCE:
LAST_ROUTE_EVENT_AT:

CURRENT_ACTOR_ROLE:
CURRENT_ACTOR_AGENT_ID:
CURRENT_ACTOR_CHAT_ID:

OWNER_GATE_STATUS:
TASK_DELTA:
TERMINAL_STATUS:

ROUTE_TRACE_PATH: .tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
NEXT_ACTION:
```

`LEDGER.md` does not replace append-only `ROUTE-TRACE.jsonl`.

### 0.5 Route reconciliation + mismatch hard gate

```text
ROUTE_RECONCILIATION: PENDING | MATCH | MISMATCH | NOT_APPLICABLE
```

On route selection: `ACTUAL=PENDING`, `RECONCILIATION=PENDING`.
On executor start: set `ACTUAL`, then `MATCH` or `MISMATCH`.

If mismatch:

```text
STATUS: BLOCKED_ROUTE_MISMATCH
EPISODE_CLOSE_ALLOWED: NO
PRODUCTION_GO_ALLOWED: NO
```

Owner route decision or corrected evidence required; no silent close.

### 0.6 Owner waiting time

```text
gate open  → OWNER_GATE_STATUS=WAITING + OWNER_GATE_OPENED_AT
Owner GO   → APPROVED + OWNER_GO_ISSUED_AT + OWNER_WAIT_DURATION_MS
rejection  → REJECTED
```

Executors must not forge these timestamps.

### 0.7 Episode closure gate (route)

Episode close requires:

```text
EXPECTED_EXECUTION_ROUTE recorded
ACTUAL_EXECUTION_ROUTE recorded or NOT_APPLICABLE
ROUTE_RECONCILIATION ∈ { MATCH, NOT_APPLICABLE }
```

Forbidden close when:

```text
PENDING
MISMATCH
missing reconciliation
```

Routes C/D use `ACTUAL=NOT_APPLICABLE` and `RECONCILIATION=NOT_APPLICABLE`.

Human-native close/handback/solo-walk/Owner-block explore policy:
`.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`
(finding vs case vs class; `POST_GREEN_OWNER`; pasteable handback;
never close from apply/update/verify).

---

## 1. RED-before-GO

### 1.1 Invariant

Owner **production** GO must not open production repair until a durable RED
proof exists for that finding, or an explicit Owner exception is recorded.

Applies to **both** implementation executors on a bug episode:

- `/opsx-fix-bug` GO
- `/opsx-apply` (when `EXPECTED_EXECUTION_ROUTE=/opsx-apply` / bug-episode case)

`/opsx-update` is **never** equivalent to production GO.

Also forbidden when `ROUTE_RECONCILIATION=MISMATCH` or
`BLOCKED_ROUTE_MISMATCH` / `BLOCKED_MISSING_ROUTE_TARGET`.

### 1.2 Preconditions for production GO

```text
OWNER_PRODUCTION_GO_ALLOWED_IF:

BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
AND OWNER_PRODUCTION_GO
AND ROUTE_RECONCILIATION ∈ { MATCH, NOT_APPLICABLE }
AND ACTUAL_EXECUTION_ROUTE matches EXPECTED when both are set
```

`RED_NOT_APPLICABLE_APPROVED` alone does **not** authorize production GO
without `BUG_CONFIRMED` and `FIX_NOW`.

Presence of new OpenSpec tasks after `/opsx-update` does **not** authorize
`/opsx-apply` production edits without the same gate.

### 1.3 Role split (policy)

| Role | Command / actor | May write |
|------|-----------------|-----------|
| Classifier | `/opsx-classify-bug` | route trace + `ROUTE_STATE` only (no OpenSpec/code) |
| Spec reviser | `/opsx-update` | OpenSpec planning artifacts; TASK_DELTA evidence; route trace |
| Bug Analyst | `/opsx-fix-bug` WITHOUT GO | `.tmp/opsx-bug-cases/**` only |
| Regression Author | `/opsx-test` | `tests/**` (+ fixtures); RED evidence in case map |
| Owner | human | production GO; `RED_NOT_APPLICABLE_APPROVED`; FINAL class verdict |
| Coordinator | human / operator (not a new agent type) | routes episode; invokes read-only fan-in assembly |
| FAN_IN_ASSEMBLER | procedure / Coordinator role | builds `FANIN.md` only; **no** Owner authority |
| Executor (fix) | `/opsx-fix-bug` GO | production after Owner GO; prefer test freeze |
| Executor (apply) | `/opsx-apply` after TASK_DELTA CHANGED | production after same RED+Owner GO gate |
| Independent Tester | `/opsx-test verify` (sole GREEN writer) | GREEN evidence; no-weaken check |

```text
COORDINATOR:
  маршрутизирует episode и вызывает read-only fan-in assembly.

FAN_IN_ASSEMBLER:
  процедура/роль Coordinator для построения FANIN.md;
  не имеет Owner authority.
```

Do **not** create a separate new agent solely to rename these roles.

Regression Author should not be the sole GREEN confirmer when a second chat
is practical.

### 1.4 Pre-GO allowed / forbidden

**Allowed before production GO:**

- read-only forensics;
- `.tmp/opsx-bug-cases/**` process writes;
- `tests/**` (+ fixtures) via `/opsx-test`;
- narrow pytest for RED evidence;
- RED evidence packets under the case map.

**Forbidden before production GO:**

- production / `app/**` (and other production paths) behavior changes;
- silent assertion weakening to obtain green;
- masking the defect via mocks/fixtures that bypass the invariant;
- commit/push as “closed” without GREEN policy when RED path was used.

### 1.5 Non-testable exception

Do not invent a fake RED or smoke-green substitute.

Required packet for exception path:

```text
REPRODUCTION_EVIDENCE
EXPECTED
OBSERVED
WHY_AUTOMATED_RED_IS_NOT_APPLICABLE
PROPOSED_POST_FIX_VERIFICATION
RISK
```

Terminal exception token (Owner only):

```text
RED_NOT_APPLICABLE_APPROVED
```

Silent skip of RED is forbidden.

---

## 2. RED / GREEN evidence and anti-weaken

### 2.1 Test identity

```text
TEST_ID = <repo-relative-path>::<pytest-nodeid>
```

At RED, also record `TEST_CONTENT_SHA256` of the authoritative test source
(and fixtures that define assertions, if separate).

### 2.2 RED_EVIDENCE contract

Durable path (recommended):

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/RED-<FINDING_ID>.md
```

Required fields:

```text
TEST_ID
BUG_CASE_ID
FINDING_ID
COMMAND
EXPECTED_FAILURE
ACTUAL_FAILURE
FAILURE_MATCH: YES | NO
PRODUCTION_HASH_BEFORE
TEST_CONTENT_SHA256
STATUS:
  RED_CONFIRMED
  | TEST_NOT_REPRODUCING
  | RED_WRONG_REASON
  | TEST_SETUP_DEFECT
  | BUG_NOT_TESTABLE
  | BLOCKED
  | TIMEOUT
```

`STATUS=RED_CONFIRMED` requires `FAILURE_MATCH: YES` and a failing run on
**unchanged** production (hash recorded).

### 2.3 GREEN_EVIDENCE contract

Durable path (recommended):

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/GREEN-<FINDING_ID>.md
```

Required fields:

```text
TEST_ID                 # must equal RED TEST_ID
BUG_CASE_ID
FINDING_ID
COMMAND
PRODUCTION_HASH_AFTER   # ≠ PRODUCTION_HASH_BEFORE unless exception path
TEST_CONTENT_SHA256     # must match RED, or justified non-weaken delta
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: …
```

### 2.4 Anti-weaken rule

- GREEN must reuse the same `TEST_ID`.
- `TEST_CONTENT_SHA256` must match the RED snapshot, **or** a recorded
  `NON_WEAKEN_DELTA` must explain every assertion/fixture change and must
  not remove or soften the failing expectation that proved the bug.
- Any weaken without Owner review ⇒ **not** `GREEN_CONFIRMED`.
- `assert_not_called()` / count-only proofs without boundary filtering remain
  insufficient for production-impact bugs (align with existing verify/test
  policy when companions land).

---

## 3. Bounded invariant hunt

Applies to root-aware sibling expansion after an invariant is defined.

### 3.1 Hard limits (MVP)

```text
MAX_HUNT_PASSES=3
MAX_DEPTH=3
MAX_ACTIVE_BRANCHES=3
PASS_3=MANDATORY_STOP
```

| Limit | Meaning |
|-------|---------|
| `MAX_HUNT_PASSES` | At most three hunt expansion passes per episode |
| `PASS_3=MANDATORY_STOP` | After the third pass, **no new branches** of the current episode are created |
| `MAX_DEPTH` | Child/finding causal depth from root ≤ 3 |
| `MAX_ACTIVE_BRANCHES` | Concurrent claimable/working branches ≤ 3 |

After pass 3 (`PASS_3=MANDATORY_STOP`): unresolved findings that cannot continue
as working branches receive a terminal disposition of:

```text
DEFERRED | BLOCKED | TIMEOUT
```

Exceeding a limit ⇒ stop expansion; record `LIMITS_CHECK: FAIL` / reason in
FANIN; remaining candidates stay backlog / deferred / blocked / timeout —
not silent open work.

### 3.2 Relation to fanout `max_children`

Fanout may still define `max_children` for packet preview. Episode
orchestration uses the **stricter** of this contract’s active-branch limit
and any fanout cap.

After `GO_ACTIVATE`, the companion command contracts are authoritative
for live OPSX orchestration.

`GRAPH.md` remains a navigation snapshot and does not override
command gates, Owner authority or durable case state.

---

## 4. Durable BRANCH_REGISTRY

### 4.1 Authority location

**Schema definition** (not a runtime instance):

```text
.cursor/pipeline/contracts/bug-episode/BRANCH_REGISTRY.md
```

**Single runtime BRANCH_REGISTRY** (only instance):

```text
RUNTIME_BRANCH_REGISTRY:
  .tmp/opsx-bug-cases/<ROOT_CASE_ID>/LEDGER.md
  section: ## BRANCH_REGISTRY
```

Do **not** create a sibling `BRANCH_REGISTRY.md` (or other second registry
file) inside the case map.

Sources to merge into that LEDGER section (read-only assemble):

- durable LEDGER / finding statuses;
- `/opsx-fanout-bug-hunt` registry / packets (preview seed only).

### 4.2 Row schema

Each started branch / finding row:

```text
FINDING_ID
PARENT_FINDING_ID | ROOT
DEPTH
TERMINAL_STATE
OWNER
CHAT_REQUIRED
TEST_ID?
RED_EVIDENCE_PATH?
GREEN_EVIDENCE_PATH?
OWNER_PRODUCTION_GO: yes|no|n/a
PRODUCTION_PATHS?
NOTES
```

### 4.3 Branch terminal states (episode vocabulary)

```text
FIXED
REJECTED
DUPLICATE
DEFERRED
BLOCKED
TIMEOUT
TEST_NOT_REPRODUCING
RED_NOT_APPLICABLE
```

Mapping to today’s durable finding statuses (companion must make explicit):

| Episode terminal | Closest durable today | FAN_IN_ELIGIBLE_TERMINAL? |
|------------------|----------------------|---------------------------|
| FIXED | `closed_fixed` + RED/GREEN linkage | yes (with evidence linkage) |
| REJECTED | `closed_false_positive` / plan-only closed | yes |
| DUPLICATE | `duplicate_*` / `absorbed_*` / `duplicate_root_observation` | yes |
| DEFERRED | `backlog` | yes (branch terminal; not class closed) |
| BLOCKED | `blocked` | yes (branch terminal; not class closed) |
| TIMEOUT | **missing today** | yes (branch terminal; not class closed) |
| TEST_NOT_REPRODUCING | **missing today** | yes (branch terminal; not class closed) |
| RED_NOT_APPLICABLE | **missing today** (+ Owner approve) | yes (conditional evidence path) |

`FAN_IN_ELIGIBLE_TERMINAL?` means the branch may be closed and included in
fan-in rollup. It does **not** mean the error class is successfully closed
or that a class lesson is allowed.

In particular, `REJECTED` and `DUPLICATE` allow finishing the branch and
including it in fan-in; they do **not** mean the error class is closed or
that a lesson is permitted.

Closing a branch ≠ closing the error class ≠ lesson gate pass.

Fan-in **must not start** while any **started** branch lacks a terminal from
the episode vocabulary above.

---

## 5. FANIN.md input / output contract

### 5.1 Assembler (MVP)

Fan-in is a **read-only rollup procedure** over the case map, performed by
`FAN_IN_ASSEMBLER` (Coordinator role; see §1.3).

- **No** `/opsx-fan-in-*` slash command in this MVP packet.
- Assembler may be a human Coordinator or a future companion step inside an
  existing command; it does **not** own class verdict or production GO.

### 5.2 Path

```text
.tmp/opsx-bug-cases/<ROOT_CASE_ID>/results/FANIN.md
```

Optional timestamped copies: `results/FANIN-<UTC>.md` with `FANIN.md` as
the latest pointer.

### 5.3 Input contract

Fan-in assemble **forbidden** until:

```text
ROOT_CASE_ID present
ROOT_FINDING_ID / ROOT_INVARIANT known
HUNT_PASSES_EXECUTED ≤ MAX_HUNT_PASSES
BRANCH_REGISTRY complete for all started branches
every started branch has TERMINAL_STATE ∈ episode terminal set
LIMITS_CHECK evaluated (depth / active / passes)
```

Input block:

```text
ROOT_CASE_ID:
ROOT_FINDING_ID:
ROOT_INVARIANT:
HUNT_PASSES_EXECUTED:
BRANCH_REGISTRY: …
LIMITS_CHECK: PASS | FAIL
LIMITS_DETAIL:
```

### 5.4 Output contract

`FANIN.md` must include at least:

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
BRANCH_SUMMARY:   # each FINDING_ID → TERMINAL + RED/GREEN/GO refs
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

Check rules:

1. Every `FIXED` row ⇒ `BUG_CASE_ID` + `TEST_ID` + RED + Owner GO + fix + GREEN
   (or documented `RED_NOT_APPLICABLE` path).
2. No weaken (`TEST_CONTENT_SHA256` / `NON_WEAKEN_DELTA`).
3. No double-fix of the same finding.
4. No conflicting production diffs across branches without Owner note.
5. One root invariant for the episode, or explicit out-of-episode separation.
6. Hunt limits not exceeded.

`BLOCKED` / `TIMEOUT` / `DEFERRED` remain visible in the report; they are
fan-in-eligible terminals but do **not** close the error class or grant
`LESSON_GATE_PASS`.

```text
FANIN_READY
  iff STATUS assembly complete
  ∧ all started branches terminal
  ∧ checks 3–6 PASS
  ∧ checks 1–2 PASS or N/A with Owner-noted exceptions recorded
  ∧ NO_OPEN_SAME_INVARIANT_CANDIDATES (HARD_BLOCK_READY)
```

Otherwise `FANIN_INCOMPLETE` (do not claim lesson gate pass).

**HARD_BLOCK_READY (episode):** any hunt/residual candidate with
`RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING` and
`STATUS ∈ {open_candidate, OPEN_CANDIDATE}` that lacks a durable
`FALSE_POSITIVE` / `OUT_OF_SCOPE` disposition **MUST** force
`FANIN_INCOMPLETE`, populate `BLOCKING_FINDINGS`, and **MUST NOT** allow
`CLOSURE_READINESS=READY_FOR_CLOSURE` or `BLOCKS_ROOT_CLOSURE=false`.
Pasteable next: `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`
(or materialize sibling then fanout). See
`.cursor/pipeline/contracts/bug-episode/FANIN.md`.

---

## 6. Lesson gate

### 6.1 Class-level lesson

A **confirmed class-level** product/logic lesson (eligible for `/opsx-learn-from-bug`
Phase 2 GO write of a class rule) requires:

```text
FANIN_READY
∧ FANIN_PATH = .tmp/opsx-bug-cases/<ROOT>/results/FANIN.md
∧ invariant coverage known
∧ FIXED rows did not lose RED/GREEN linkage
∧ input ≠ root-only anecdote without branch rollup
```

When those hold, the gate outcome is:

```text
LESSON_GATE_PASS
CLASS_STATUS: may close or promote per Owner FINAL (§9.2)
CLASS_LEVEL_GO_WRITE: allowed only with Owner FINAL PROMOTE_CLASS_LESSON
```

### 6.2 Otherwise (incomplete fan-in / no lesson gate pass)

When fan-in is incomplete, missing, or lesson preconditions in §6.1 fail,
the paired outcome is:

```text
LESSON_CANDIDATE_ONLY
CLASS_STATUS: OPEN
```

```text
CLASS_LEVEL_GO_WRITE: FORBIDDEN
```

while `LESSON_GATE_PASS` is absent (i.e. until §6.1 conditions hold and the
gate explicitly passes).

Allowed: Phase 1 analyze, `needs_more_evidence`, `local_case_note_only`.

**Forbidden:** confirmed class lesson + class-level GO write of a reusable
class rule while `FANIN_INCOMPLETE`, without `FANIN_PATH`, or without
`LESSON_GATE_PASS`.

Finding-local notes remain allowed without FANIN; they must not be labeled
as class promotion.

### 6.3 Lesson input fields (from FANIN)

```text
ERROR_CLASS
ROOT_CAUSE_PATTERN
WHY_CONTROLS_MISSED
SIBLING_VARIANTS
FIX_PATTERNS
REGRESSION_TEST_PATTERN
PREVENTION_RULE
REUSABLE_CHECK
REMAINING_EXCEPTIONS
FANIN_PATH
ROOT_CASE_ID
```

---

## 7. No new invariant inside the current episode

```text
NEW_INVARIANT_FROM_BRANCH: FORBIDDEN inside the open episode
```

If a branch reveals a **different** invariant / causal root:

- treat as `CREATE_SEPARATE_ROOT_CANDIDATE` / backlog / separate case;
- do **not** retarget the current episode’s root invariant mid-flight;
- start a **new** episode only after Owner decision (typically after FANIN
  or explicit Owner split).

Same-invariant siblings stay in-episode under hunt bounds.

---

## 8. `LEARNING_READY` vs `FANIN_READY`

| Token | Owner today | Means | Does **not** mean |
|-------|-------------|-------|-------------------|
| fanout `LEARNING_READY` | `/opsx-fanout-bug-hunt` | children have stable adjudication readiness for learning **registry** preview | all branches terminal; RED/GREEN complete; class lesson allowed |
| episode `FANIN_READY` | this contract / FANIN.md | all started branches terminal + FANIN checks | production GO; automatic class write |

**Hard rule:** never treat fanout `LEARNING_READY=true` as `FANIN_READY`.
Companion updates must keep the names distinct in command text and handoffs.

---

## 9. Owner-only production GO and final class verdict

### 9.1 Production GO

- Exact Owner token `GO` opens **production** repair only under §1 for
  `/opsx-fix-bug` **and** for bug-episode `/opsx-apply` after
  `TASK_DELTA: CHANGED`.
- Executor commands must not invent Owner approval.
- `/opsx-update` is never production GO.
- New/changed tasks after update are not automatic apply authorization.
- Test authoring for RED does **not** require a separate Owner production GO
  (uses `/opsx-test` path).
- Classify-first (§0.1) is required before selecting an implementation route.

### 9.2 Final class verdict

After `FANIN_READY`, Owner decides exactly one:

```text
PROMOTE_CLASS_LESSON      → /opsx-learn-from-bug GO (with FANIN_PATH)
KEEP_LESSON_CANDIDATE_ONLY
CLOSE_EPISODE_NO_CLASS_LESSON
SPLIT_NEW_EPISODE         → new case for separate invariant
```

Coordinator / FAN_IN_ASSEMBLER / agent must not auto-promote class rules.

### 9.3 Process-contract lessons

Command-contract / process Bugbot lessons remain on
`/opsx-admin-command-promote-process-lesson` — **not** this episode FANIN path.

---

## 10. Companion implementation status (live)

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
CANDIDATE_WORKTREE_BEHAVIOR_CHANGED: YES
LIVE_WORKSPACE_BEHAVIOR_CHANGED: YES
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
ACTIVATION_SOURCE_COMMIT: bcd132ccf62712f6dd0d00a18a0c26f7dc8c8179
INDEPENDENT_TEST_RESULT: T1–T18 PASS
TARGETED_RETEST_RESULT: PASS
```

Companion contracts are live and authoritative for product/logic bug
episodes. Creating `/opsx-fan-in-*` remains forbidden unless a later Owner
design chooses slash UX.

`GRAPH.md` / `META.md` are refreshed via `/opsx-pipeline UPDATE GO` as
navigation snapshots only — they do not replace this contract or command
gates.

---

## Human return shape (live episode)

```text
WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

---

## Self-check (this artifact)

- [x] Marked `LIVE_PROCESS_CONTRACT` / `RUNTIME_ENFORCEMENT: ACTIVE` /
      `LIVE_COMMAND_BEHAVIOR_CHANGED: YES` / `GO_ACTIVATE: ISSUED`
- [x] Classify-first mandatory before implementation route (§0.1)
- [x] Routes A–D (implementation / spec / FP / out-of-scope) defined
- [x] TASK_DELTA CHANGED|UNCHANGED → apply vs fix-bug (§0.2)
- [x] ROUTE-TRACE v2 + LEDGER `## ROUTE_STATE` (§0.3–0.4)
- [x] Route reconciliation + MISMATCH hard gate (§0.5)
- [x] Owner waiting fields (§0.6)
- [x] Episode closure requires MATCH|NOT_APPLICABLE (§0.7)
- [x] Route D requires ROUTE_TARGET_PROCESS_ID
- [x] RED-before-GO for both `/opsx-fix-bug` and bug-episode `/opsx-apply`
- [x] `/opsx-update` ≠ production GO; task delta ≠ auto apply permission
- [x] RED/GREEN + anti-weaken defined
- [x] Hunt bounds 3/3/3 + `PASS_3=MANDATORY_STOP` defined
- [x] BRANCH_REGISTRY + `FAN_IN_ELIGIBLE_TERMINAL?` defined
- [x] FANIN.md I/O defined without new slash command
- [x] Coordinator / FAN_IN_ASSEMBLER terminology (no new agent)
- [x] Lesson gate: class only after `FANIN_READY`; else
      `LESSON_CANDIDATE_ONLY` + `CLASS_STATUS: OPEN` +
      `CLASS_LEVEL_GO_WRITE: FORBIDDEN` without `LESSON_GATE_PASS`
- [x] No new invariant inside episode
- [x] `LEARNING_READY` ≠ `FANIN_READY`
- [x] Owner-only production GO + final class verdict
- [x] Companion status: `LIVE_ACTIVATED` + `INDEPENDENT_TEST_PASS`;
      single runtime BRANCH_REGISTRY = LEDGER `## BRANCH_REGISTRY`
)
