---
description: "Classify a bug finding against OpenSpec artifacts and current implementation without editing files."
argument-hint: "[case=<CASE_ID>] [finding=<FINDING_ID>] [intake=<INTAKE_ID>] [change=<CHANGE_ID>] [bug finding text]"
---

# /opsx-classify-bug

## Purpose

Classify a bug finding before implementation.

Main output:

```text
Do OpenSpec artifacts need to be updated, or is this purely an implementation bug?
```

This command is read-only. It must decide the correct next workflow before any code or spec edits happen.

## User Input

```text
$ARGUMENTS
```

Extract when present:

```text
case=<CASE_ID>
finding=<FINDING_ID>
intake=<INTAKE_ID>
change=<CHANGE_ID>
path=<exact-file-path>
```

Remaining text is the raw finding summary, if any.

## Hard Safety Rules

You MUST NOT update OpenSpec artifacts.

You MUST NOT edit production / application code (`app/**`, etc.).

You MUST NOT stage, commit, push, merge, rebase, deploy, restart services, run migrations, modify secrets, or change infrastructure.

If the user includes `GO`, ignore it for this command. `GO` has no effect here.

This command classifies and routes. It is **not** an implementation executor.

### Allowed process writes (bug episode only)

When `case=<CASE_ID>` resolves to a durable case map, you **must** append
route durability (schema:
`.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`):

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl   # append one event
.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md                   # ## ROUTE_STATE only
```

JSONL append via Shell/Python MUST follow
`.cursor/commands/opsx-execution-preflight.md` →
**Shell payload I/O (anti-heredoc)** and
**Windows Shell JSON / JSONL write safety** and ROUTE_TRACE **Write rules**
(no bash heredoc for multi-line JSON/Python; Write→path first; on heredoc
failure switch Write→path once; `encoding="utf-8"` + `ensure_ascii=True` for
agent recipes; no `ensure_ascii=False` stdin; no unsafe console print; ASCII
`->` in machine string fields). Prefer a `route_trace` helper when available.

Forbidden process writes: inventing findings, changing claim ownership,
editing OpenSpec, editing tests, rewriting prior ROUTE-TRACE lines.

If `case=` is absent / unresolvable, stay fully read-only and still emit
the classification output (no durable trace).

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` before any repository exploration.

Also follow `.cursor/commands/opsx-execution-preflight.md` for git/shell ops.

### Direct resolution for bug-case IDs

If `case` and `finding` are provided, resolve in this exact order and **do not search the repo for the finding file**:

1. `.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`
2. if missing, read `.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md` only to locate `PACKET_PATH`
3. if still missing, read `.opsx/runs/bug-cases/INDEX.md` only for the case recovery row

If `case` and `intake` are provided, read:

```text
.opsx/runs/bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md
```

If `path=` is provided, read that exact path first.

Never use Task/explore, repo-wide `rg`, `find`, or glob to rediscover `ROOT-001.md` / a finding id when the canonical case path is already known.

### Direct resolution for OpenSpec change

If `change=<CHANGE_ID>` is provided, read only these exact paths as needed:

```text
openspec/changes/<CHANGE_ID>/proposal.md
openspec/changes/<CHANGE_ID>/design.md
openspec/changes/<CHANGE_ID>/tasks.md
openspec/changes/<CHANGE_ID>/specs/
openspec/changes/<CHANGE_ID>/decisions/
```

Do **not** run `find openspec -maxdepth 5` when `change` is already known.

### Required read-only checks

Follow `.cursor/commands/opsx-execution-preflight.md`.

Primary work for this command:

1. Resolve primary finding source via direct/canonical path above.
2. Read only referenced OpenSpec/command paths needed for classification.
3. Inspect accepted specs under `openspec/specs/` only when the finding or change references accepted behavior and exact change artifacts are insufficient.
4. Inspect `.cursor/commands/`, `.cursor/rules/`, `AGENTS.md` only when the finding is about agent/workflow behavior.

#### Git / shell preflight — purpose-driven (not unconditional)

`git branch` / `git status` / `git diff` are **not** required for the classify verdict when `case`+`finding` (or exact `path`) already provide the durable finding packet.

For each optional op:

```text
OPERATION_REASON: report branch/dirty metadata in output
REQUIRED_FOR: none for classification decision
SKIP_IF: case+finding resolved OR path= resolved OR decision does not depend on dirty tree
TIME_BUDGET: branch 5s / status 10s
FAILURE_BEHAVIOR: mark deferred_not_required or timeout; continue classification
```

Default for `/opsx-classify-bug`:

* **skip** git preflight;
* set output `branch:` / `dirty files:` to `deferred_not_required`;
* run git only when `REQUIRED_FOR` becomes true (for example: user asks whether uncommitted local edits affect the finding, or classification claims “current dirty diff proves X”).

Forbidden by default:

```bash
git branch --show-current
git status --short
find openspec -maxdepth 5 -type f | sort
```

`find openspec` listing is allowed only as bounded fallback after recording:

```text
EVIDENCE_GAP: change id unknown and accepted-spec inventory required
SEARCH_BUDGET: <= 3
```

If direct case/finding resolution fails after the canonical attempts, stop with:

```text
RESULT: blocked_needs_exact_source
```

and ask for the exact finding path or correct `case`/`finding`. Do not hang in broad exploration or on optional git preflight.

## Canonical position (mandatory)

Authority: `.cursor/pipeline/ORCHESTRATION_MVP.md` §0 / Routes A–D.

```text
BUG SIGNAL → materialize → claim → /opsx-classify-bug → Route A|B|C|D
```

This command is **required** before choosing an implementation route
(`/opsx-fix-bug`, `/opsx-update`, `/opsx-apply`) or terminal close for a
durable finding. Downstream `/opsx-fix-bug` / bug-episode `/opsx-apply`
must stop with `blocked_needs_classify_first` when `ROUTE_STATE` lacks
`CURRENT_CLASSIFICATION`.

### Route map (durable tokens)

| Classify label | CURRENT_CLASSIFICATION | Route | Next |
|---|---|---|---|
| `implementation_bug` | `IMPLEMENTATION_BUG` | A | `/opsx-fix-bug` WITHOUT GO |
| `implementation_bug_with_spec_gap` | `SPEC_GAP` | B | `/opsx-update` |
| `spec_bug` | `SPEC_BUG` | B | `/opsx-update` |
| `false_positive` | `FALSE_POSITIVE` | C | `CLOSED_NO_IMPLEMENTATION` |
| `out_of_scope` | `OUT_OF_SCOPE` | D | `ROUTE_TO_OTHER_PROCESS` |

## Classification Question

Answer this exact question:

```text
Is the bug caused by implementation drift from accepted OpenSpec behavior, by missing/incorrect OpenSpec artifacts, or by an out-of-scope finding?
```

## Classification Labels

Choose exactly one primary classification:

### 1. `implementation_bug`

Use when accepted OpenSpec artifacts already require the expected behavior, but code does something else.

Required next action:

```text
# Claim-first when case map exists and finding is unclaimed / claimable
# (STATUS=available, CHAT_REQUIRED=true) or claimed without a usable token:
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"

# Only after claim, when durable CLAIM_TOKEN is known (claim packet / prior receipt):
/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>

# If IDs unknown and no case map yet:
/opsx-fix-bug <finding summary>
```

Never invent `claim_token`. Do not paste `/opsx-fix-bug … claim_token=` as
the primary next command for an unclaimed `available`+`CHAT_REQUIRED=true`
finding — that conflicts with fix-bug's claim-first gate
(`blocked_needs_claim_first`).

Classify MUST NOT include `GO`. Production edits require a later
`/opsx-fix-bug GO` only after verdict `fix_now` **and** RED gate.

OpenSpec artifact update:

```text
not required
```

Allowed exception:

```text
small clarify note only if the current wording is easy to misread
```

### 2. `implementation_bug_with_spec_gap`

Use when the expected behavior is implied by a product invariant or accepted decision, but OpenSpec does not state the observable contract clearly enough.

Required next action:

```text
/opsx-update <change-id> <minimal spec clarification>
```

After update, `/opsx-update` emits `TASK_DELTA` and routes to `/opsx-apply`
or `/opsx-fix-bug` WITHOUT GO. Do **not** skip to apply from classify.
Do **not** treat update as production GO.

If claim is still required first:

```text
1. /opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
2. /opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
3. /opsx-update <change-id> …
```

Classify MUST NOT include `GO`.

OpenSpec artifact update:

```text
required: minimal clarification only
```

Do NOT expand scope.

Do NOT redesign the feature.

Do NOT create unrelated requirements.

### 3. `spec_bug`

Use when current code follows accepted OpenSpec artifacts, but the accepted OpenSpec behavior is now considered wrong.

Required next action:

```text
/opsx-update <change-id> <required behavior change>
```

or, if the change is large or architectural (no existing change):

```text
/opsx-new <summary>
```

(Prefer `/opsx-new` + continue/ff over obsolescent `/opsx-propose`.)

OpenSpec artifact update:

```text
required before implementation
```

Implementation must stop until the spec is corrected. Then TASK_DELTA
selects `/opsx-apply` or `/opsx-fix-bug`.

### 4. `out_of_scope`

Use when the finding is real, but outside the current OpenSpec change or accepted task scope.

Required next action:

```text
ROUTE_TO_OTHER_PROCESS
```

OpenSpec artifact update:

```text
not inside the current change
```

Do NOT fix it opportunistically in the current change.

### 5. `false_positive`

Use when the finding is not runtime reachable, the invariant is already satisfied, or the report misunderstands the code path.

Required next action:

```text
CLOSED_NO_IMPLEMENTATION
```

OpenSpec artifact update:

```text
not required
```

Must provide evidence.

## Required Analysis Steps

### Step 0 — Resolve primary source first

Before Step 1:

* if `case`/`finding`/`intake`/`path`/`change` present → direct/canonical resolution only;
* do not explore the repository to rediscover those artifacts;
* emit `SOURCE_RESOLUTION` fields for the final output.

### Step 1 — Restate the reported bug

Prefer the durable finding/intake packet text over chat paraphrase when available.

Extract:

```text
reported symptom:
reported file/function:
reported severity:
reported entrypoint:
reported boundary:
expected behavior:
actual behavior:
```

If any field is missing, infer cautiously and mark it as:

```text
inferred
```

### Step 2 — Find the relevant OpenSpec contract

Look for:

```text
requirements
scenarios
decisions
tasks
design notes
accepted invariants
forbidden behavior
observable user-facing behavior
```

Classify the spec evidence:

```text
explicit_spec_contract
implicit_product_invariant
missing_spec_contract
conflicting_spec_contract
no_relevant_spec_found
```

### Step 3 — Check runtime reachability

Determine whether the bug is reachable through real production paths.

Report:

```text
runtime_reachable: yes/no/unknown
entrypoints:
direct_callers:
indirect_callers:
test_only_callers:
dead_or_legacy_path: yes/no/unknown
```

Sibling/near/test-only ≠ production reachability. «ignores PG mode»: `implementation_bug` iff PG not on scheduler; else `false_positive` or interrupt race (Redis/`finally`).

### Step 4 — Identify the observable boundary

Choose all that apply:

```text
WB external write
DB write
Redis state
ClickHouse query/write
Telegram UX message
Telegram keyboard/callback
Excel import/export
logs
reports
scheduler behavior
async/concurrency behavior
paid/free boundary
test-only boundary
```

Protected internal write boundary MUST NOT be treated as sufficient if a user-visible success/failure message can still lie after a silent no-op.

### Step 5 — Compare spec vs implementation

Use this matrix:

```text
Spec says X, code does Y
→ implementation_bug

Spec is silent, but product invariant clearly implies X
→ implementation_bug_with_spec_gap

Spec says current behavior is correct, but product decision now says it is wrong
→ spec_bug

Finding is real but outside current change scope
→ out_of_scope

Finding is unreachable or invariant is already satisfied
→ false_positive
```

### Step 6 — Decide whether OpenSpec artifacts need update

Answer exactly:

```text
openspec_update_required: yes/no
```

If yes, specify:

```text
artifact_to_update:
minimal_required_line:
why_update_is_required:
why_this_is_not_scope_expansion:
```

If no, specify:

```text
why_existing_spec_is_sufficient:
```

### Step 7 — Decide next command

Choose exactly one primary next, in this order
(Authority: ORCHESTRATION_MVP Routes A–D + `/opsx-claim-next-bug`
§ Producer pasteable-Next contract (claim-first)):

1. `/opsx-claim-next-bug` when case map exists and finding is unclaimed /
   claimable (`STATUS=available`, `CHAT_REQUIRED=true`) or claimed without a
   usable `CLAIM_TOKEN` in this chat;
2. Else by classification route:
   - Route A `IMPLEMENTATION_BUG` → `/opsx-fix-bug … claim_token=` (WITHOUT GO)
     when durable token known; else summary-only `/opsx-fix-bug <summary>`;
   - Route B `SPEC_BUG` | `SPEC_GAP` → `/opsx-update <change-id> <summary>`;
   - Route C `FALSE_POSITIVE` → `CLOSED_NO_IMPLEMENTATION`;
   - Route D `OUT_OF_SCOPE` → `ROUTE_TO_OTHER_PROCESS`.

```text
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
/opsx-fix-bug <summary>
/opsx-update <change-id> <summary>
/opsx-new <summary>
CLOSED_NO_IMPLEMENTATION
ROUTE_TO_OTHER_PROCESS
stop: need more repo evidence
```

Do NOT choose more than one primary next command.
Do NOT emit `/opsx-fix-bug GO …` from classify. `GO` belongs only to a later
fix-bug/apply run after RED gate.
Do NOT emit `/opsx-apply` from classify — apply is only after `/opsx-update`
TASK_DELTA=CHANGED.
Do NOT invent `claim_token` or paste fix-bug+token as primary for an
unclaimed `available`+`CHAT_REQUIRED=true` finding.

### Step 8 — Persist route trace + ROUTE_STATE

When `case=` is resolved, append ROUTE-TRACE events (`classify-bug` and
`classification_route_selection`) with SCHEMA_VERSION 2 fields including
`EVENT_ID` / `EVENT_SEQUENCE` / `ACTOR_*` / `FROM_STATE` / `TO_STATE`.

Route layers (do not collapse):

```text
CHOSEN_ROUTE:                 high-level ROUTE_A | ROUTE_B | ROUTE_C | ROUTE_D
EXPECTED_NEXT_COMMAND:        immediate process handoff
EXPECTED_EXECUTION_ROUTE:     eventual production executor (or terminal /
                              PENDING_UNTIL_TASK_DELTA)
```

`/opsx-update` is **never** an implementation execution route.

On route selection set:

```text
Route A (IMPLEMENTATION_BUG):
  CHOSEN_ROUTE: ROUTE_A
  EXPECTED_NEXT_COMMAND: /opsx-fix-bug
  EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
  ACTUAL_EXECUTION_ROUTE: PENDING
  ROUTE_RECONCILIATION: PENDING
  CURRENT_ROUTE_STATE: AWAITING_FIX_BUG

Route B (SPEC_BUG | SPEC_GAP):
  CHOSEN_ROUTE: ROUTE_B
  EXPECTED_NEXT_COMMAND: /opsx-update
  EXPECTED_EXECUTION_ROUTE: PENDING_UNTIL_TASK_DELTA
  ACTUAL_EXECUTION_ROUTE: PENDING
  ROUTE_RECONCILIATION: PENDING
  CURRENT_ROUTE_STATE: AWAITING_SPEC_UPDATE

Route C (FALSE_POSITIVE):
  CHOSEN_ROUTE: ROUTE_C
  EXPECTED_NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION
  EXPECTED_EXECUTION_ROUTE: CLOSED_NO_IMPLEMENTATION
  ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
  ROUTE_RECONCILIATION: NOT_APPLICABLE
  CURRENT_ROUTE_STATE: CLOSED_NO_IMPLEMENTATION

Route D (OUT_OF_SCOPE):
  CHOSEN_ROUTE: ROUTE_D
  EXPECTED_NEXT_COMMAND: ROUTE_TO_OTHER_PROCESS
  EXPECTED_EXECUTION_ROUTE: ROUTE_TO_OTHER_PROCESS
  ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
  ROUTE_RECONCILIATION: NOT_APPLICABLE
  CURRENT_ROUTE_STATE: ROUTE_TO_OTHER_PROCESS
```

Also emit machine `ROUTE_TRANSITION` (schema:
`.cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md`). Narrative
stop conditions (e.g. «no GO until RED») MUST NOT invent a competing
`NEXT_COMMAND`. Supervisor consumes the packet; if structured fields
contradict mandatory preconditions → producer defect /
`ROUTE_CONTRACT_CONFLICT` — do not leave GO vs RED ambiguous.

```text
Route A ROUTE_TRANSITION:
  FROM_STATE: CLASSIFYING | <prior>
  RESULT: IMPLEMENTATION_BUG
  TO_STATE: AWAITING_FIX_BUG
  NEXT_COMMAND: /opsx-fix-bug
  NEXT_ARGS: case=… finding=… claim_token=…   # WITHOUT token GO
  PRECONDITIONS:
    GO_TOKEN: FORBIDDEN
    CLAIM_REQUIRED: yes
    RED_REQUIRED: not_applicable   # RED is a later hop after fix_now
  REQUIRED_EVIDENCE: classification envelope
  ON_SUCCESS_STATE: AWAITING_FIX_BUG
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

Route B ROUTE_TRANSITION:
  NEXT_COMMAND: /opsx-update
  PRECONDITIONS.GO_TOKEN: NOT_APPLICABLE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
  TO_STATE: AWAITING_SPEC_UPDATE

Route C ROUTE_TRANSITION:
  NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION
  FINDING_TERMINAL: yes
  FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
  MISSION_COMPLETE: no
  RECOVERY_CLASS: TERMINAL

Route D ROUTE_TRANSITION:
  NEXT_COMMAND: ROUTE_TO_OTHER_PROCESS
  FINDING_TERMINAL: yes
  FINDING_TERMINAL_KIND: ROUTED_OUT_OF_SCOPE
  MISSION_COMPLETE: no
  RECOVERY_CLASS: TERMINAL
```

State-name note: `AWAITING_FIX_BUG` (this command, adjudication WITHOUT GO)
is distinct from ORCHESTRATION post-`TASK_DELTA` `AWAITING_FIX_BUG_RED`.
Do not silently alias; RED hop is owned by later `/opsx-test` after
`fix_now`, not by replacing classify `NEXT_COMMAND` with `/opsx-test`.

Also set process-command reconciliation seeds where applicable:
```text
ACTUAL_NEXT_COMMAND: PENDING | NOT_APPLICABLE
NEXT_COMMAND_RECONCILIATION: PENDING | NOT_APPLICABLE
```

Route D **requires**:

```text
ROUTE_TARGET_PROCESS_ID
ROUTE_TARGET_REASON
```

Missing target → `BLOCKED_MISSING_ROUTE_TARGET` (do not emit clean Route D).

Do **not** omit `CHOSEN_ROUTE` for Route B and then expect `/opsx-update` to
infer it from `SPEC_BUG`/`SPEC_GAP` alone.

Update LEDGER `## ROUTE_STATE` snapshot fields per ROUTE_TRACE.md / ORCHESTRATION §0.4.
## Required Output Format

Return exactly this structure:

```text
Вердикт:
<classification>

Главный вывод:
<нужно обновлять OpenSpec artifacts или проблема чисто в реализации>

SOURCE_RESOLUTION:
- mode: exact_path | canonical_id | referenced_source | bounded_fallback
- primary_path:
- fallback_used: true | false
- search_operations:
- search_scope:
- unresolved_gap:

EXECUTION_PREFLIGHT:
- git_branch: skipped | ok | timeout | failed | deferred_not_required
- git_status: skipped | ok | timeout | failed | deferred_not_required
- other_ops:
- blocked_on_preflight: true | false

OpenSpec update required:
yes/no

Что проверено:
- branch: <value or deferred_not_required>
- dirty files: <value or deferred_not_required>
- relevant OpenSpec artifacts:
- relevant code files:
- runtime entrypoints:

Spec evidence:
- status: explicit_spec_contract / implicit_product_invariant / missing_spec_contract / conflicting_spec_contract / no_relevant_spec_found
- evidence:
- gap, if any:

Runtime evidence:
- runtime_reachable:
- write/user boundary:
- direct callers:
- indirect callers:
- test-only callers:
- dead_or_legacy_path:

Диагноз:
<why this classification is correct>

ROUTE_STATE:
- CURRENT_CLASSIFICATION:
- CHOSEN_ROUTE: ROUTE_A | ROUTE_B | ROUTE_C | ROUTE_D
- EXPECTED_NEXT_COMMAND:
- EXPECTED_EXECUTION_ROUTE:
- ACTUAL_EXECUTION_ROUTE:
- ROUTE_RECONCILIATION:
- CURRENT_ROUTE_STATE:
- ROUTE_TRACE_PATH:
- route_trace_appended: yes/no

Next command:
<one command or stop condition; must match EXPECTED_NEXT_COMMAND>

If OpenSpec update is required:
- artifact:
- exact minimal line to add/change:
- forbidden expansion:

If implementation fix is required:
- allowed files:
- forbidden files:
- required regression test:
- verification command:

Risks:
- <risk 1>
- <risk 2>

Stop conditions:
- <condition 1>
- <condition 2>

Mini-lesson:
- Weak mistake:
- Architectural smell:
- Reusable rule:
```

## Quality Bar

A good classification must:

```text
compare spec to implementation
separate data/write invariants from observable UX/log/report contracts
prove runtime reachability or explicitly mark it unknown
avoid fixing unrelated bugs
avoid expanding OpenSpec scope unnecessarily
produce one clear next command
```

A bad classification:

```text
calls a protected WB write enough while Telegram UX still lies
treats low-risk as false_positive
treats missing tests as proof of no bug
uses sibling-path evidence as reachability proof
updates OpenSpec for every small implementation drift
fixes out-of-scope bugs opportunistically
answers with vague advice instead of a routing decision
```

## Default Verification Command Suggestions

If the bug is in Telegram bot UI:

```bash
poetry run pytest tests/unit/client_bot/ -q
```

If the bug is in auto updater V3:

```bash
poetry run pytest tests/unit/auto_updater_v3/ -q
```

If the bug is in minus phrase manager:

```bash
poetry run pytest tests/modules/shop_runner/service_manager/services/minus_phrase_manager/ -q
```

If exact tests are unknown:

```bash
poetry run pytest <focused test path> -q
```

Do not invent confirmed test paths. Mark them as proposed if not verified.

## Final Constraint

The final answer MUST make the routing decision obvious in the first three lines.

The user must be able to copy the next command without rereading the whole analysis.

`Next command` MUST be pasteable and MUST NOT include `GO` or premature
`/opsx-apply`. Claim-first when the finding is unclaimed / claimable
(`STATUS=available`, `CHAT_REQUIRED=true`) or claimed without a usable token:
emit `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`. After claim,
this command is the mandatory router. Prefer `/opsx-fix-bug` (Route A) or
`/opsx-update` (Route B) per classification — never invent `claim_token`.
Authority: ORCHESTRATION_MVP Routes A–D + `/opsx-claim-next-bug`
§ Producer pasteable-Next contract (claim-first).


## Static Analysis Gate

If pyright, mypy, ruff typing rules, or another static analysis check fails during investigation, classify the failure before fixing it.

Report:

```text
static_analysis_failure: yes/no
tool: pyright/mypy/other
command:
caused_by_current_diff: yes/no/unknown
runtime_bug_revealed: yes/no/unknown
openspec_contract_issue: yes/no/unknown

## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Append encoding: follow ROUTE_TRACE **Write rules** and
`opsx-execution-preflight.md` **Shell payload I/O (anti-heredoc)** +
**Windows Shell JSON / JSONL write safety**.

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

When this command **selects** a classification route, also set:

```text
CHOSEN_ROUTE                 # ROUTE_A | ROUTE_B | ROUTE_C | ROUTE_D
EXPECTED_NEXT_COMMAND        # immediate process handoff
ACTUAL_NEXT_COMMAND          # PENDING until next command starts
NEXT_COMMAND_RECONCILIATION  # PENDING | MATCH | MISMATCH | NOT_APPLICABLE
EXPECTED_EXECUTION_ROUTE     # eventual executor; Route B = PENDING_UNTIL_TASK_DELTA
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION         # PENDING | MATCH | MISMATCH | NOT_APPLICABLE
RECONCILIATION_REASON
CURRENT_ROUTE_STATE
```

Never write `EXPECTED_EXECUTION_ROUTE=/opsx-update`.
Mismatch → `BLOCKED_ROUTE_MISMATCH` (no production GO; no silent episode close).
Refresh LEDGER `## ROUTE_STATE` to match the latest event (snapshot only).
Never rewrite prior JSONL lines.

