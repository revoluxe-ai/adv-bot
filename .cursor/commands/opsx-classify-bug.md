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

You MUST NOT modify files.

You MUST NOT create files.

You MUST NOT update OpenSpec artifacts.

You MUST NOT edit code.

You MUST NOT stage, commit, push, merge, rebase, deploy, restart services, run migrations, modify secrets, or change infrastructure.

If the user includes `GO`, ignore it for this command. `GO` has no effect here.

This command only classifies and routes.

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` before any repository exploration.

Also follow `.cursor/commands/opsx-execution-preflight.md` for git/shell ops.

### Direct resolution for bug-case IDs

If `case` and `finding` are provided, resolve in this exact order and **do not search the repo for the finding file**:

1. `.tmp/opsx-bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`
2. if missing, read `.tmp/opsx-bug-cases/<CASE_ID>/LEDGER.md` only to locate `PACKET_PATH`
3. if still missing, read `.tmp/opsx-bug-cases/INDEX.md` only for the case recovery row

If `case` and `intake` are provided, read:

```text
.tmp/opsx-bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md
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
`/opsx-fix-bug GO` only after verdict `fix_now`.

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
1. /opsx-update <change-id> <minimal spec clarification>
2. then claim-first if needed:
   /opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
   — or, only when CLAIM_TOKEN is already known:
   /opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
   (or /opsx-fix-bug <finding summary> without GO if IDs unknown)
```

Classify MUST NOT include `GO` on step 2.

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

or, if the change is large or architectural:

```text
/opsx-propose <new change>
```

OpenSpec artifact update:

```text
required before implementation
```

Implementation must stop until the spec is corrected.

### 4. `out_of_scope`

Use when the finding is real, but outside the current OpenSpec change or accepted task scope.

Required next action:

```text
create a separate lightweight bugfix or new OpenSpec change
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
stop; do not edit
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

Choose exactly one. For implementation routes, prefer in this order
(Authority: `/opsx-claim-next-bug` § Producer pasteable-Next contract
(claim-first)):

1. `/opsx-claim-next-bug` when case map exists and finding is unclaimed /
   claimable (`STATUS=available`, `CHAT_REQUIRED=true`) or claimed without a
   usable `CLAIM_TOKEN` in this chat;
2. `/opsx-fix-bug … claim_token=` only when durable `CLAIM_TOKEN` is already
   known;
3. `/opsx-fix-bug <summary>` when IDs / case map are unknown.

```text
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
/opsx-fix-bug <summary>
/opsx-update <change-id> <summary>
/opsx-propose <summary>
stop: false positive
stop: need more repo evidence
```

Do NOT choose more than one primary next command.
Do NOT emit `/opsx-fix-bug GO …` from classify. `GO` belongs only to a later
fix-bug run after verdict `fix_now`.
Do NOT invent `claim_token` or paste fix-bug+token as primary for an
unclaimed `available`+`CHAT_REQUIRED=true` finding.

If `implementation_bug_with_spec_gap`, the next command may include two ordered substeps:

```text
1. /opsx-update <change-id> <minimal spec clarification>
2. /opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
   — or, only when CLAIM_TOKEN is already known:
   /opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
   (or /opsx-fix-bug <summary> without GO if IDs unknown)
```

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

Next command:
<one command or stop condition>

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

`Next command` for implementation routes MUST be pasteable and MUST NOT include
`GO`. Claim-first when the finding is unclaimed / claimable
(`STATUS=available`, `CHAT_REQUIRED=true`) or claimed without a usable token:
emit `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`. Prefer
`/opsx-fix-bug` with durable `case=` / `intake=` / `finding=` /
`claim_token=` only when that token is already known — never invent it.
Authority: `/opsx-claim-next-bug` § Producer pasteable-Next contract
(claim-first).


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
