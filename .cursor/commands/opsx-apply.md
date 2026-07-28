---
name: /opsx-apply
id: opsx-apply
category: Workflow
description: Implement tasks from an OpenSpec change (Experimental)
---

Implement tasks from an OpenSpec change.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Before changing code, resolve decision paths from the selected change context/`artifactPaths.decisions` first. Prefer exact listed paths over a full `openspec/decisions/**` walk. Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`: when the change name is known, do not rediscover it by scanning all changes; do not gate apply on unconditional `git status`—run git only when dirty-tree / branch identity is REQUIRED_FOR safe implementation. Search `openspec/decisions/**/*.md` only for remaining gaps after direct context paths are read (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Do **not** equate budget exhaustion with “no decision exists”: if ownership / layering / write-path / domain-invariant gaps remain unresolved after that budget (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Use `Architecture Decision Missing` only when lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision. Implementation must cite relevant decisions in progress or completion notes. If planned code placement contradicts an accepted decision, stop before editing code and return `NO_GO` with the conflicting decision path. If placement depends on a proposed decision, use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied before deciding whether code can proceed. Passing tests are not sufficient if placement violates a decision.

**Canonical testing rule:** Before implementation, read `.cursor/rules/testing-rules.mdc` as the only general test-design/execution policy. Do not treat `.cursor/rules/TESTING_RULES.mdc` as policy (migration pointer only). Do not copy large test-policy blocks into this command; follow the authority split below.

**Authority split for tests:**

- `.cursor/rules/testing-rules.mdc` — general test-design and execution
- `openspec/config.yaml` → `rules.tasks` — task-generation obligations
- `/opsx-invariant` → change-specific `TEST_COVERAGE_PACKET`
- `/opsx-apply` — implementation + test materialization for owning tasks
- `/opsx-verify` — independent adequacy and archive verdict

**Input**: Optionally specify a change name (e.g., `/opsx:apply add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx:apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - `planningHome`, `changeRoot`, and `actionContext`: planning scope and edit constraints
   - Which artifact contains the tasks (typically "tasks" for spec-driven, check status for others)

3. **Get apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns:
   - `contextFiles`: artifact ID -> array of concrete file paths (varies by schema)
   - Progress (total, complete, remaining)
   - Task list with status
   - Dynamic instruction based on current state

   **Handle states:**
   - If `state: "blocked"` (missing artifacts): show message, suggest using `/opsx:continue`
   - If `state: "all_done"`: congratulate, suggest `/opsx-verify <change-name>` (not archive readiness)
   - Otherwise: proceed to implementation

4. **Read context files**

   Read file paths listed under `contextFiles` from the apply instructions output,
   under execution-preflight Read I/O budgets (prefer sequential; parallel max 2;
   large artifacts via section Read when only a part is needed).
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks, and optional decisions when present
   - Other schemas: follow the contextFiles from CLI output

5. **Read canonical testing rule and optional TEST_COVERAGE_PACKET**

   - Always read `.cursor/rules/testing-rules.mdc` before editing code or tests.
   - Search current change artifacts / context files for a `TEST_COVERAGE_PACKET` block.
   - If found, extract its required behavioral / sibling / residual scenarios, reality and mocking constraints, and minimum test level.
   - Absence of `TEST_COVERAGE_PACKET` does **not** block legacy apply.
   - Packet status (`ready` / `provisional` / `not_materialized` / `not_applicable`) by itself does **not** block implementation.
   - Do not invent mandatory scenarios without evidence from spec, decision, task, invariant, or a materialized packet.
   - Do not modify an invariant only to make a test convenient.
   - Do not declare final test adequacy or archive readiness; that belongs to `/opsx-verify`.

6. **Perform Architecture Decision Lookup**

   - Resolve paths from `contextFiles.decisions` / `artifactPaths.decisions` / user-supplied paths first.
   - Read `openspec/decisions/index.md` only if still needed to locate candidates.
   - Search/read further under `openspec/decisions/` **only** for remaining gaps after direct context (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Never dump the full decision tree.
   - If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Budget exhaustion is not proof that no decision exists.
   - Read existing proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the change touches ownership, layering, write paths, or domain invariants and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision, output `Architecture Decision Missing` and pause unless the artifacts already include a proposed decision.
   - If a proposed decision is required or present, get `openspec instructions decisions --change "<name>" --json` and apply `rules.decisions` before evaluating placement.
   - Compare planned implementation placement against accepted/proposed decisions before editing code.
   - If placement conflicts with an accepted decision, return `NO_GO` and do not edit code.

7. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Whether `TEST_COVERAGE_PACKET` was found (present / absent) and its status if present
   - Dynamic instruction from CLI

8. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Materialize materialized test obligations from the owning task together with that task when they are required by:
     - the task text;
     - `openspec/config.yaml` → `rules.tasks`;
     - `.cursor/rules/testing-rules.mdc`;
     - and/or a present `TEST_COVERAGE_PACKET` with applicable required scenarios
   - When those obligations apply:
     - do not create phantom model/DTO fields or impossible states;
     - do not fully mock the causal boundary under test;
     - materialize allowed sibling and residual/repeated-invocation scenarios when the packet/spec/task makes them mandatory;
     - run focused/targeted tests for the changed slice (and adjacent tests when a neighboring contract/workflow is affected)
   - Do **not** mark the task complete (`- [ ]` → `- [x]`) if its mandatory tests fail
   - Mark task complete in the tasks file only after required implementation and mandatory focused tests for that task succeed: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

9. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest `/opsx-verify <change-name>` as the next step (do not claim archive readiness)
   - If paused: explain why and wait for guidance

**Output During Implementation**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation happening...]
✓ Task complete

Working on task 4/7: <task description>
[...implementation happening...]
✓ Task complete
```

**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

### Completed This Session
- [x] Task 1
- [x] Task 2
...

Implementation tasks complete. Next: `/opsx-verify <change-name>`.
Do not claim archive readiness from apply alone.
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```



## Bug-episode RED + Owner GO gate

Authority: `.cursor/pipeline/ORCHESTRATION_MVP.md` §1.

When `/opsx-apply` is the bug-episode implementation executor
(`ROUTE_STATE.EXPECTED_EXECUTION_ROUTE=/opsx-apply` or request includes
`case=`/`finding=` after `TASK_DELTA: CHANGED`):

Production implementation is allowed only if:

```text
BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
AND OWNER_PRODUCTION_GO
```

Hard stops:

* missing classify → `blocked_needs_classify_first` → `/opsx-classify-bug …`
* missing/failed TASK_DELTA YES route → do not apply; return to update/fix-bug
* missing RED → `blocked_needs_red_before_go` → `/opsx-test case= finding=`
* missing Owner GO → do not edit production; wait for Owner

`/opsx-update` is never a substitute for Owner GO.
`TASK_DELTA: CHANGED` is never automatic production permission.

On bug-episode apply start set:

```text
ACTUAL_EXECUTION_ROUTE: /opsx-apply
ROUTE_RECONCILIATION: MATCH | MISMATCH
```

MISMATCH -> BLOCKED_ROUTE_MISMATCH (no production edits).
Also require TASK_DELTA: CHANGED and EXPECTED_EXECUTION_ROUTE=/opsx-apply.


Append ROUTE-TRACE event for `apply`. Update `## ROUTE_STATE`.

Normal OpenSpec apply **without** bug-episode case context keeps the
existing change-lifecycle apply behavior (no RED gate).


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

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- Always read `.cursor/rules/testing-rules.mdc` before implementation
- Read `TEST_COVERAGE_PACKET` when present in change artifacts/context; absence does not block legacy apply
- Packet status alone does not block implementation and does not equal verify/archive verdict
- Always perform Architecture Decision Lookup before code edits
- Stop with `NO_GO` when the decision-lookup fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved
- Stop with `NO_GO` when planned placement conflicts with an accepted architecture decision
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- After implementing tasks, treat any new production/exported symbol whose only callers are tests as dead surface: wire it into a runtime-reachable path or remove it before completion. Passing tests do not prove wiring.
- Update task checkbox immediately after completing each task; never mark `[x]` when mandatory tests for that task fail
- When a completed task closes a decision-delta, sync every status mirror in the same pass: the tasks.md checkbox, the decision.md review-checklist annotation, and the design.md checklist/status mirror if present. Do not leave a shipped delta marked "proposed / not yet applied".
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names
- Do not invent mandatory test scenarios without spec/decision/task/invariant/packet evidence
- Do not change invariants for test convenience
- Do not declare final adequacy or archive readiness; next step after completion is `/opsx-verify <change-name>`

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
