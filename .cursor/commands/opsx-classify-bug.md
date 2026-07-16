---
description: "Classify a bug finding against OpenSpec artifacts and current implementation without editing files."
argument-hint: "[bug finding text] [optional OpenSpec change-id]"
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

## Hard Safety Rules

You MUST NOT modify files.

You MUST NOT create files.

You MUST NOT update OpenSpec artifacts.

You MUST NOT edit code.

You MUST NOT stage, commit, push, merge, rebase, deploy, restart services, run migrations, modify secrets, or change infrastructure.

If the user includes `GO`, ignore it for this command. `GO` has no effect here.

This command only classifies and routes.

## Required Read-Only Checks

First inspect the current repository state:

```bash
git branch --show-current
git status --short
```

Then inspect relevant OpenSpec artifacts:

```bash
find openspec -maxdepth 5 -type f | sort
```

If a change-id is provided, inspect:

```text
openspec/changes/<change-id>/proposal.md
openspec/changes/<change-id>/design.md
openspec/changes/<change-id>/tasks.md
openspec/changes/<change-id>/specs/
```

Also inspect relevant accepted specs:

```text
openspec/specs/
```

If the reported behavior references Cursor/GitHub/Codex/agent workflow, also inspect:

```text
.cursor/commands/
.cursor/skills/
.cursor/rules/
.github/prompts/
.github/skills/
.github/PULL_REQUEST_TEMPLATE.md
AGENTS.md
CLAUDE.md
CODEX.md
README.md
```

Only report files that actually exist.

If a path is not confirmed, write:

```text
unconfirmed path: <path>
```

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
/opsx-fix-bug GO <finding summary>
```

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
1. update the smallest relevant OpenSpec artifact line
2. then run /opsx-fix-bug GO <finding summary>
```

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

### Step 1 — Restate the reported bug

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

Choose exactly one:

```text
/opsx-fix-bug GO <summary>
/opsx-update <change-id> <summary>
/opsx-propose <summary>
stop: false positive
stop: need more repo evidence
```

Do NOT choose more than one primary next command.

If `implementation_bug_with_spec_gap`, the next command may include two ordered substeps:

```text
1. /opsx-update <change-id> <minimal spec clarification>
2. /opsx-fix-bug GO <summary>
```

## Required Output Format

Return exactly this structure:

```text
Вердикт:
<classification>

Главный вывод:
<нужно обновлять OpenSpec artifacts или проблема чисто в реализации>

OpenSpec update required:
yes/no

Что проверено:
- branch:
- dirty files:
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
