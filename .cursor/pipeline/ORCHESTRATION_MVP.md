# OPSX bug-episode orchestration MVP (draft process contract)

```text
STATUS: DRAFT_PROCESS_CONTRACT
IMPLEMENTATION_STATUS: CANDIDATE_IMPLEMENTED
VALIDATION_STATUS: NOT_VALIDATED
LIVE_WORKSPACE_BEHAVIOR_CHANGED: NO
CANDIDATE_WORKTREE_BEHAVIOR_CHANGED: YES
RUNTIME_ENFORCEMENT: NOT_ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: NO
COMPANION_UPDATES_REQUIRED: PARTIAL_IN_CANDIDATE
OWNER_APPROVAL_SCOPE: CONTRACT_ARTIFACT_ONLY
GO_ACTIVATE: NOT_ISSUED
```

## Document role

This file is a **shared process contract** for product/logic bug episodes.

It is **not**:

- a live command;
- a slash `/opsx-fan-in-*` command;
- an authority override of `/opsx-verify`, `/opsx-archive`, `/opsx-commit`,
  or command GO gates;
- a replacement for `.cursor/pipeline/GRAPH.md` (GRAPH remains
  `navigation_snapshot_only` until a separate `/opsx-pipeline` UPDATE GO).


**Candidate implementation:** companion command/schema updates may
exist only on branch `opsx/orchestration-mvp-candidate`. Live workspace
commands remain unchanged until `GO_ACTIVATE`. Do not claim
`RUNTIME_ENFORCEMENT: ACTIVE`.

Until companion updates land and this document is promoted past
`DRAFT_PROCESS_CONTRACT` with `RUNTIME_ENFORCEMENT: ACTIVE`, live OPSX
commands keep their **current** write-gates and handoffs. Operators may
**voluntarily** follow this contract; enforcement is not claimed.

**Dual-truth risk:** this draft and live command text may disagree. Live
commands win for runtime behavior until companions are applied.

---

## Scope

**In scope:** product / behavioral bug episodes that may:

1. require a regression proof before production repair;
2. expand via root-aware invariant sibling hunt;
3. promote a **class-level** process lesson after all started branches terminate.

**Out of scope:**

- typing-only packets (`/opsx-fix-types`, static-check);
- process / command-contract defects
  (`/opsx-admin-command-fix-command-defects`,
  `/opsx-admin-command-promote-process-lesson`);
- OpenSpec change apply/verify/archive lifecycle (except optional later GRAPH
  navigation edges);
- `/opsx-static-check` fan-in (different domain).

---

## Target episode sequence (not live until companions)

```text
BUG SIGNAL
  → /opsx-fix-bug WITHOUT GO
  → BUG_CONFIRMED + verdict fix_now
  → /opsx-test (author + run RED; no production GO)
  → RED_CONFIRMED | fail-states | BUG_NOT_TESTABLE → Owner exception
  → OWNER_PRODUCTION_GO_ALLOWED_IF:

       BUG_CONFIRMED
       AND FIX_NOW
       AND (
         RED_CONFIRMED
         OR RED_NOT_APPLICABLE_APPROVED
       )

     # RED_NOT_APPLICABLE_APPROVED alone does NOT allow GO
     # without BUG_CONFIRMED and FIX_NOW.
  → /opsx-fix-bug GO  (production only; test freeze by default)
  → same TEST_ID re-run → GREEN_CONFIRMED
  → optional bounded invariant hunt / fan-out children
  → per-branch RED → Owner GO → fix → GREEN → terminal
  → ALL started branches terminal
  → assemble FANIN.md (read-only rollup; no slash required)
  → FANIN_READY
  → /opsx-learn-from-bug with FANIN_PATH=…  (class-level)
  → Owner FINAL class verdict
```

Finding-scoped notes without class promotion may skip FANIN; they must not
claim a confirmed class lesson or class-rule GO write.

---

## 1. RED-before-GO

### 1.1 Invariant

Owner **production** GO must not open production repair until a durable RED
proof exists for that finding, or an explicit Owner exception is recorded.

### 1.2 Preconditions for production GO

```text
OWNER_PRODUCTION_GO_ALLOWED_IF:

BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
```

`RED_NOT_APPLICABLE_APPROVED` alone does **not** authorize production GO
without `BUG_CONFIRMED` and `FIX_NOW`.

### 1.3 Role split (policy)

| Role | Command / actor | May write |
|------|-----------------|-----------|
| Bug Analyst | `/opsx-fix-bug` WITHOUT GO | `.tmp/opsx-bug-cases/**` only |
| Regression Author | `/opsx-test` | `tests/**` (+ fixtures); RED evidence in case map |
| Owner | human | production GO; `RED_NOT_APPLICABLE_APPROVED`; FINAL class verdict |
| Coordinator | human / operator (not a new agent type) | routes episode; invokes read-only fan-in assembly |
| FAN_IN_ASSEMBLER | procedure / Coordinator role | builds `FANIN.md` only; **no** Owner authority |
| Executor | `/opsx-fix-bug` GO | production after Owner GO; prefer test freeze |
| Independent Tester | separate chat when practical | GREEN confirm; no-weaken check |

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
and any fanout cap once companions enforce this file.

Until companions: live fanout rules remain authoritative at runtime.

---

## 4. Durable BRANCH_REGISTRY

### 4.1 Authority location

Authoritative episode branch table lives under the root case map:

```text
.tmp/opsx-bug-cases/<ROOT_CASE_ID>/
  LEDGER.md          # durable statuses (existing)
  BRANCH_REGISTRY    # section in LEDGER.md and/or sibling file
                     # (exact persistence shape = companion packet)
```

Sources to merge (read-only assemble):

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
```

Otherwise `FANIN_INCOMPLETE` (do not claim lesson gate pass).

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

- Exact Owner token `GO` (per live `/opsx-fix-bug` semantics when companions
  align) opens **production** repair only under §1.
- Executor commands must not invent Owner approval.
- Test authoring for RED does **not** require a separate Owner production GO
  (uses `/opsx-test` path once companions align).

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

## 10. Required companion updates (separate subsequent packet)

This OWNER_APPROVAL_SCOPE covers **only** this contract artifact.
The following must **not** be edited under the present GO; they need a
**separate** Owner GO packet (design/implement), e.g. OPTION_B style:

1. **`.cursor/commands/opsx-fix-bug.md`**
   - Decouple tests from production under one GO.
   - After `fix_now`, pasteable next → `/opsx-test` / RED, not production GO.
   - Production GO path requires RED evidence or `RED_NOT_APPLICABLE_APPROVED`.

2. **`.cursor/commands/opsx-test.md`**
   - Bug-case handoff (`case` / `finding`).
   - Emit `RED_EVIDENCE` / durable `results/RED-*.md`.
   - Explicit `FAILURE_MATCH`; forbid weaken-for-green.

3. **`.cursor/commands/opsx-learn-from-bug.md`**
   - Class-level path requires `FANIN_PATH` + `FANIN_READY`.
   - Else force `LESSON_CANDIDATE_ONLY` / no class GO write.

4. **`.cursor/commands/opsx-materialize-bug-queue.md`**
   - Persist BRANCH_REGISTRY fields, RED/GREEN paths, FANIN pointer.
   - Durable terminals for `TIMEOUT`, `TEST_NOT_REPRODUCING`,
     `RED_NOT_APPLICABLE` (or explicit map).

5. **`.cursor/commands/opsx-fanout-bug-hunt.md`**
   - Keep `LEARNING_READY` ≠ `FANIN_READY`.
   - Align expansion with hunt bounds when seeding registry.

6. **`.cursor/commands/opsx-bug-hunt.md`** (as needed)
   - Encode `MAX_HUNT_PASSES` / depth / active-branch stop conditions.

7. **`.cursor/pipeline/GRAPH.md` + `META.md`**
   - Only via `/opsx-pipeline` UPDATE GO: insert `red_*`, `fan_in_ready`,
     and lesson edges; do not silent-edit.

8. **Optional:** `.cursor/rules/testing-rules.mdc` soft note on RED-before-GO.

9. **Explicit non-goal of companions unless Owner later asks:**
   - Do **not** create `/opsx-fan-in-*` unless a later design chooses slash UX.

Until that packet: `RUNTIME_ENFORCEMENT: NOT_ACTIVE`,
`LIVE_COMMAND_BEHAVIOR_CHANGED: NO`.

---

## Human return shape (when voluntarily following this draft)

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

- [x] Marked `DRAFT_PROCESS_CONTRACT` / `NOT_ACTIVE` / `LIVE_COMMAND_BEHAVIOR_CHANGED: NO`
- [x] RED-before-GO defined (`OWNER_PRODUCTION_GO_ALLOWED_IF` grouping)
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
- [x] Companion list deferred to later packet
)
