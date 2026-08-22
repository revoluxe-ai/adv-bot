---
description: "Adjudicate whether a bug yields a transferable process lesson, then optionally write only an approved packet to an existing authoritative target."
argument-hint: "[GO] [case=<CASE_ID>] [finding=<FINDING_ID>] [intake=<INTAKE_ID>] [change=<CHANGE_ID>] [target=<path>] [approval=<state>]"
---

# /opsx-learn-from-bug

Purpose: decide whether a reviewed **product / logic** bug contains a
**transferable process lesson**, route it to the correct authority class, and
only then optionally write an **approved** change to an **existing** process
source.

**Branch boundary:** command-contract / process Bugbot lessons (F6 —
`.cursor/commands/**`, rules, skills, static-check contracts) belong to
`/opsx-admin-command-promote-process-lesson`, not this command. Typing stays on
`/opsx-fix-types` / static-check (no learning command).

This command is **not** a universal raw-incident sink.

It MUST separate:

1. raw / product finding;
2. process-learning adjudication;
3. source routing;
4. approved write.

Raw incident text and Mini-lesson blocks are **not** automatically:

- a permanent rule;
- an approved guardrail;
- a candidate source update;
- a mandatory worklog entry.

## Modes

### Phase 1 — ANALYZE (default, no `GO`)

Read-only semantic adjudication.

No file writes.
No worklog creation.
No automatic `GO` suggestion unless a write packet is ready and allowed.

### Phase 2 — WRITE (`GO`)

Allowed only when Phase 1 (same chat or explicit replay of the Phase-1 packet) prepared an approved write packet.

GO mode is active only when the user invokes:

- `/opsx-learn-from-bug GO`
- `/opsx-learn-from-bug:GO`

## Hard safety

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

MUST NOT:

- create `.cursor/worklogs/bug-learning.md` or any universal learning sink;
- use `.cursor/worklogs/bug-learning.md` as automatic default target;
- use `DOTO/WORKLOG.md` as learning sink;
- invent a new learning hierarchy;
- write product code, tests, OpenSpec product artifacts, or unrelated commands;
- promote one case into global policy without promotion criteria + approval;
- re-run full forensics / classification when durable finding + prior classify output suffice;
- treat capture convenience as owner approval.

Local output vocabulary of this command (not global lifecycle statuses):

```text
no_learning_update
local_case_note_only
candidate_guardrail
candidate_source_update
needs_more_evidence
```

Phase-1 VERDICT values:

```text
learning_candidate_ready
no_learning_update
local_case_note_only
needs_more_evidence
owner_decision_required
```

## Inputs

```text
case=<CASE_ID>
finding=<FINDING_ID>
intake=<INTAKE_ID>
change=<CHANGE_ID>
target=<path>                 # optional explicit existing target
approval=<owner_approved|...> # optional; required for GO when disposition needs owner
GO
```

Prefer durable case/finding over chat paraphrase.

## Phase 1 — ANALYZE (no GO)

## Class-level lesson gate (orchestration MVP)

Schema: `.cursor/pipeline/contracts/bug-episode/LESSON_GATE.md`.

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```

Finding-local / `local_case_note_only` **without** FANIN remains allowed and
must not be labeled as class promotion.

### Class-level confirmed lesson — preconditions

Class-level lesson (eligible for Phase 2 GO write of a class rule) requires:

```text
FANIN_READY
AND FANIN_PATH exists
  (.tmp/opsx-bug-cases/<ROOT>/results/FANIN.md)
AND coverage assessed
AND FIXED branches contain RED/GO/FIX/GREEN evidence linkage
```

Also require durable FANIN checks consistent with
`.cursor/pipeline/contracts/bug-episode/FANIN.md`.

When preconditions fail → **mandatory**:

```text
LESSON_CANDIDATE_ONLY
CLASS_STATUS: OPEN
CLASS_LEVEL_GO_WRITE: FORBIDDEN
```

Root patch or a single finding alone **cannot** create a confirmed
class-level lesson.

Owner FINAL after `FANIN_READY` (surface in Phase 1 output when relevant):

```text
PROMOTE_CLASS_LESSON
KEEP_LESSON_CANDIDATE_ONLY
CLOSE_EPISODE_NO_CLASS_LESSON
SPLIT_NEW_EPISODE
```

Fanout `LEARNING_READY=true` alone does **not** unlock class lesson.


### 1. Direct-first source load

If `case` + `finding` provided, read in order:

1. `.tmp/opsx-bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`
2. optional intake / CASE.md / prior same-chat `/opsx-classify-bug` or `/opsx-fix-bug` output
3. do **not** rediscover via repo-wide search
4. do **not** run unconditional git status/branch

### 2. Separate levels (mandatory)

Extract and keep separate:

```text
PRODUCT_FINDING:
PROCESS_LESSON:
CANDIDATE_GUARDRAIL:
CANDIDATE_SOURCE_UPDATE:
```

Rules:

* `PRODUCT_FINDING` = literal runtime/wiring/fix fact of this case.
* `PROCESS_LESSON` = transferable process insight, if any.
* Do not promote product finding into process lesson by default.
* Do not invent guardrails that are only “add a regression test for this bug”.

### 3. Promotion check

A `candidate_guardrail` or `candidate_source_update` is allowed only if **all** hold:

- evidence is confirmed (from durable finding / classify / cited sources);
- the rule applies wider than the literal fix of this finding;
- there is a concrete consumer (named command, rule file, verify gate, test policy, etc.);
- the rule prevents a repeatable class of mistakes;
- the rule does not duplicate an existing approved source;
- proposed placement matches the authority map;
- the change does not create needless bureaucracy;
- one case is not auto-converted into global policy.

If any criterion fails, lower disposition to `no_learning_update`, `local_case_note_only`, or `needs_more_evidence`.

### 4. LEARNING_DISPOSITION

Choose exactly one:

| Disposition | Meaning | GO offered? |
|---|---|---|
| `no_learning_update` | no transferable process lesson | **no** |
| `local_case_note_only` | note belongs only in this case map / finding packet | **no** (unless owner explicitly orders a case-local note write with exact packet) |
| `candidate_guardrail` | reusable process guardrail candidate | only after target+approval gate |
| `candidate_source_update` | update to an existing authoritative source | only after target+approval gate |
| `needs_more_evidence` | lesson possible but under-evidenced | **no** |

Default for “this is just the product bug / this fix needs a regression test” → `no_learning_update` or `local_case_note_only`.

### 5. Target resolution (no universal sink)

**Forbidden:**

```text
.cursor/worklogs/bug-learning.md   # not an automatic default
automatic create-on-GO of any new learning file
```

`TARGET_RESOLUTION.mode` MUST be one of:

```text
exact_existing_target
candidate_existing_target
no_target_needed
needs_target_extraction
owner_decision_required
```

Routing:

1. If disposition is `no_learning_update` or `needs_more_evidence` → `no_target_needed`.
2. If disposition is `local_case_note_only` → prefer existing case finding/result path; do not invent worklogs. Usually `no_target_needed` for Phase 1 (note stays in output / optional later case update outside this command unless owner supplies exact case path + approval).
3. If disposition is `candidate_guardrail` / `candidate_source_update`:
   - if `target=` provided and exists → validate authority fit → `exact_existing_target` or reject;
   - else map rule class → authority map;
   - if unique existing file fits → `candidate_existing_target` (still needs approval for GO);
   - if ambiguous → bounded search (≤ 3 targeted ops) over process sources only;
   - return at most **two** candidates;
   - if still unresolved → `needs_target_extraction` or `owner_decision_required`;
   - **never create** a new file in Phase 1 or Phase 2 unless owner explicitly ordered creation of a named existing hierarchy file (default: never create).

### Authority map (rule class → existing sources)

Use as routing hints, not as auto-write license:

| Rule class | Prefer existing sources |
|---|---|
| test design / stub vs production shape | `.cursor/rules/testing-rules.mdc` |
| OPSX command behavior / search / preflight | `.cursor/commands/opsx-*.md`, `.cursor/commands/opsx-source-resolution.md`, `.cursor/commands/opsx-execution-preflight.md` |
| architecture ownership / write-path | `openspec/decisions/**`, change `decisions/` |
| verify / archive gates | `openspec/policies/VERIFY_POLICY.md`, `/opsx-verify` |
| explore / WORKLOG handling | `openspec/policies/EXPLORE_POLICY.md` |
| bug-case durability / intake | `.cursor/commands/opsx-materialize-bug-queue.md`, `.cursor/commands/opsx-fix-bug.md` |

Bounded fallback search roots (only when needed):

```text
.cursor/commands/
.cursor/rules/
openspec/policies/
openspec/decisions/
```

Budget: ≤ 3 targeted operations. Exact filename/symbol first. No Task-explore. No new files.

### 6. Duplication check

Before proposing a write, check whether an existing approved source already states the lesson.

If duplicate:

* disposition becomes effectively no new write;
* VERDICT: `no_learning_update` (or keep candidate but `WRITE_ALLOWED: false` with pointer to existing source);
* cite the existing path.

### 7. Phase-1 write policy

```text
WRITE_ALLOWED: false
```

Never propose GO when disposition is:

- `no_learning_update`
- `local_case_note_only` (default)
- `needs_more_evidence`

Propose GO only when:

- disposition is `candidate_guardrail` or `candidate_source_update`;
- `TARGET_RESOLUTION.mode` is `exact_existing_target` or `candidate_existing_target` with one chosen existing path;
- `PROPOSED_CHANGE` is exact;
- approval state is present or clearly marked `owner_decision_required` (then VERDICT=`owner_decision_required`, still no GO until approved).

If owner approval is required and absent:

```text
VERDICT: owner_decision_required
WRITE_ALLOWED: false
NEXT_ACTION: ask owner to approve exact proposed change against PROPOSED_TARGET
```

## Required Phase-1 output

Return exactly:

```text
VERDICT:
- learning_candidate_ready | no_learning_update | local_case_note_only | needs_more_evidence | owner_decision_required

PRODUCT_FINDING:
PROCESS_LESSON:
CANDIDATE_GUARDRAIL:
CANDIDATE_SOURCE_UPDATE:

LEARNING_DISPOSITION:
- no_learning_update | local_case_note_only | candidate_guardrail | candidate_source_update | needs_more_evidence

EVIDENCE:
REUSABILITY:
- wider_than_literal_fix: yes | no | unknown
CONSUMER:
- <named consumer or none>
DUPLICATION_CHECK:
- status: none_found | duplicate_of_existing | needs_check
- existing_source:
PROMOTION_CRITERIA:
- evidence_confirmed:
- wider_than_literal_fix:
- concrete_consumer:
- prevents_repeatable_class:
- not_duplicate:
- authority_fit:
- no_extra_bureaucracy:
- not_single_case_global_policy:
- overall: pass | fail

TARGET_RESOLUTION:
- mode: exact_existing_target | candidate_existing_target | no_target_needed | needs_target_extraction | owner_decision_required
- would_create_on_go: false
PROPOSED_TARGET:
- <existing path or none>
- candidates:   # max 2
PROPOSED_CHANGE:
- <exact diff/section text or none>

WRITE_ALLOWED: false

LESSON_GATE_STATUS: LESSON_GATE_PASS | LESSON_CANDIDATE_ONLY | n/a
CLASS_STATUS: OPEN | n/a | …
CLASS_LEVEL_GO_WRITE: FORBIDDEN | allowed_after_owner_final | n/a
FANIN_PATH:

SOURCE_RESOLUTION:
- mode:
- primary_path:
- fallback_used:
- search_operations:
- search_scope:
- unresolved_gap:

EXECUTION_PREFLIGHT:
- git_branch: deferred_not_required
- git_status: deferred_not_required
- other_ops:
- blocked_on_preflight: false

NEXT_ACTION:
- <no GO | owner approval question | extraction prompt | stop>
```

When `needs_target_extraction`, `NEXT_ACTION` MUST be a ready read-only extraction prompt (≤3 searches, named roots, no file creation).

## Phase 2 — GO gate

### Class-level GO additional gate

Phase 2 GO that writes a **class-level** reusable rule is allowed only if
Phase-1 packet shows `LESSON_GATE_PASS` (or equivalent) with
`FANIN_PATH` + `FANIN_READY` + coverage + FIXED evidence linkage, **and**
Owner FINAL `PROMOTE_CLASS_LESSON` (or `approval=` equivalent).

Otherwise keep:

```text
CLASS_LEVEL_GO_WRITE: FORBIDDEN
LESSON_CANDIDATE_ONLY
CLASS_STATUS: OPEN
```


`/opsx-learn-from-bug GO` is allowed only if all are true:

1. Phase-1 packet exists in the same chat (or user pastes it) with:
   - `LEARNING_DISPOSITION` ∈ {`candidate_guardrail`, `candidate_source_update`};
   - `PROPOSED_TARGET` = exact existing file;
   - `PROPOSED_CHANGE` = exact text/diff;
   - `PROMOTION_CRITERIA.overall: pass`;
   - `DUPLICATION_CHECK` not blocking;
2. Approval state is satisfied:
   - owner said approval in-chat; or
   - `approval=owner_approved` is present; or
   - the command contract of the target already makes this class of edit owner-approved for the active task (rare; must be cited).
3. GO does **not** re-adjudicate the whole case from scratch; it applies the prepared packet.

GO MUST NOT:

- automatically create a universal worklog;
- write raw `BUG_LEARNING_PACKET` instead of the adjudicated proposed change;
- turn a local note into policy;
- choose a different target than `PROPOSED_TARGET`;
- set `would_create_on_go: true`.

On success, append/patch only the approved proposed change into the existing target, then report files changed.

If GO is invoked without a ready packet:

```text
VERDICT: blocked
REASON: missing_phase1_write_packet
WRITE_ALLOWED: false
NEXT_ACTION: run Phase 1 without GO
```

## Current-case acceptance anchor (ROOT-001)

For:

```text
CASE_ID: BUGCASE-ABHOLD-SHOPALLOW-20260726T014312Z
FINDING_ID: ROOT-001
```

Phase 1 MUST show separately at least:

```text
PRODUCT_FINDING:
Telegram Enable передаёт shop_id=None, потому что читает отсутствующий AdvSetting.shop_id.

PROCESS_LESSON / candidate:
Тестовый stub может скрыть wiring defect, если добавляет атрибут, отсутствующий в production ORM path.
```

Then MUST decide whether that lesson is:

- only a regression-test requirement of the current fix → usually `no_learning_update` or `local_case_note_only`;
- a reusable testing guardrail → maybe `candidate_guardrail` toward `.cursor/rules/testing-rules.mdc` **if** promotion criteria pass and not duplicate;
- duplicate of existing testing-rules language about stubs / production shape;
- under-evidenced → `needs_more_evidence`.

It MUST NOT automatically propose writing to `.cursor/worklogs/bug-learning.md`.
`would_create_on_go` MUST be `false`.

## Acceptance tests

### A. Literal-only incident

→ `no_learning_update` or `local_case_note_only`  
→ GO not offered.

### B. Reusable lesson with existing target

→ `candidate_guardrail` or `candidate_source_update`  
→ exact existing target  
→ proposed change  
→ GO possible only after approval.

### B2. Bugbot residual miss (product/logic)

When the lesson is «Bugbot нашёл то, что primary hunter пропустил»:

→ prefer existing target
  `.cursor/commands/opsx-project-bug-hunt.md`
  (checklist section `Project hunt checklist (learning target)`);
→ disposition `candidate_source_update`;
→ after GO, owner should re-run `/opsx-project-bug-hunt` on a similar
  `base..head` to verify the new check would have caught the miss;
→ do **not** route this class to F6 admin promote unless the miss was a
  process-contract defect.

### C. Reusable lesson without confirmed target

→ `needs_target_extraction` or `owner_decision_required`  
→ ready extraction prompt  
→ no file created.

### D. Duplicate existing rule

→ no new write  
→ cite existing source.

### E. Current ROOT-001

→ semantic adjudication runs  
→ no automatic default worklog  
→ `would_create_on_go: false`.

## Required invariants

MUST adjudicate before any write.

MUST keep product finding distinct from process lesson.

MUST NOT use `.cursor/worklogs/bug-learning.md` as automatic default sink.

MUST NOT create learning files automatically on GO.

MUST NOT offer GO for `no_learning_update`, `local_case_note_only`, or `needs_more_evidence`.

MUST bound target search to ≤ 3 ops and ≤ 2 candidates.

MUST treat capture/write as separate from optimization/promotion into broader policy when approval is missing.

## Out of scope for this command

- product implementation;
- writing application tests as the learning action;
- changing the current OpenSpec product change as a side effect;
- migrating existing cases;
- redesigning the whole OPSX lifecycle;
- creating a new learning hierarchy;
- process-contract / command-defect learning (use
  `/opsx-admin-command-promote-process-lesson`);
- emitting `DESIGN_BRIEF_READY` for new admin commands (use promote →
  `/opsx-admin-command-design-command`).



## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Mandatory identity/order fields on every event:

```text
SCHEMA_VERSION
EVENT_ID
EVENT_SEQUENCE
CASE_ID
FINDING_ID
EVENT_TYPE
COMMAND
ACTOR_ROLE
ACTOR_AGENT_ID
ACTOR_CHAT_ID
FROM_STATE
TO_STATE
STARTED_AT
COMPLETED_AT
DURATION_MS
TERMINAL_STATUS
PREVIOUS_EVENT_ID
```

Actor identity:

```text
ACTOR_AGENT_ID: CURRENT_CHAT_AGENT  # if no separate agent id
ACTOR_CHAT_ID:  durable stable chat label (required; not free-text role alone)
```

When this command **selects** or **executes** an implementation route, also set:

```text
EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION   # PENDING | MATCH | MISMATCH | NOT_APPLICABLE
RECONCILIATION_REASON
```

Mismatch → `BLOCKED_ROUTE_MISMATCH` (no production GO; no silent episode close).
Refresh LEDGER `## ROUTE_STATE` to match the latest event (snapshot only).
Never rewrite prior JSONL lines.

