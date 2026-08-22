---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.6.0"
---

Implement tasks from an OpenSpec change.

This skill is a concise adapter. It is **not** the authoritative apply contract.

**Before implementation, always read and follow:**

1. `.cursor/commands/opsx-apply.md` — current apply workflow contract (including Architecture Decision Lookup and source-resolution/preflight semantics already present there)
2. `.cursor/rules/testing-rules.mdc` — canonical general test-design/execution policy

Do **not** treat `.cursor/rules/TESTING_RULES.mdc` as policy (deprecated migration pointer only).
Do **not** treat `.cursor/skills/**` as authority over `.cursor/commands/**`.
Do **not** duplicate the full testing policy or a conflicting local Architecture Decision Lookup here.

**Authority split:**

- `.cursor/commands/opsx-apply.md` → current apply workflow contract
- `.cursor/rules/testing-rules.mdc` → general test-design/execution policy
- `openspec/config.yaml` → `rules.tasks` → task-generation obligations
- `/opsx-invariant` → `TEST_COVERAGE_PACKET` → change-specific test obligations
- `/opsx-verify` → independent adequacy and archive verdict
- `/opsx-pyright-strict-coverage` → post-apply recommend when production `.py` changed
- `/opsx-external-call-coverage` → after pyright PASS; external-surface test coverage audit

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

0. **Read authoritative apply contract**

   Read `.cursor/commands/opsx-apply.md` and follow its current steps, Architecture Decision Lookup, testing obligations, pause conditions, checkbox semantics, and completion routing.
   Also read `.cursor/rules/testing-rules.mdc` before editing code or tests.

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx-apply <other>`).

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
   - If `state: "blocked"` (missing artifacts): show message, suggest using `/opsx-continue` / openspec-continue-change
   - If `state: "all_done"`: congratulate, then follow **Post-apply next-step recommend** in `.cursor/commands/opsx-apply.md` (not archive readiness)
   - Otherwise: proceed to implementation

4. **Read context files**

   Read `contextFiles` paths under execution-preflight Read I/O budgets (prefer sequential; parallel max 2; section Read for large artifacts when only part is needed).
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks, and optional decisions when present
   - Other schemas: follow the contextFiles from CLI output

5. **Optional TEST_COVERAGE_PACKET**

   - Inspect current change artifacts/context for a `TEST_COVERAGE_PACKET` block.
   - Absence of packet does **not** block legacy apply.
   - Packet status alone does **not** block implementation.
   - Do not invent mandatory scenarios without spec/decision/task/invariant/packet evidence.
   - Do not declare final test adequacy or archive readiness; that belongs to `/opsx-verify`.

6. **Perform Architecture Decision Lookup**

   Follow the Architecture Decision Lookup contract in `.cursor/commands/opsx-apply.md` exactly (context/`artifactPaths.decisions` first; source-resolution/preflight semantics; `NO_GO` on placement conflict). Do not use a conflicting local ADL copy.

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
   - Materialize mandatory test obligations with the owning task when required by task text, `rules.tasks`, `testing-rules.mdc`, and/or a present `TEST_COVERAGE_PACKET`
   - When those obligations apply:
     - do not create phantom model/DTO fields or impossible states;
     - do not fully mock the causal boundary under test;
     - materialize required allowed sibling and residual/repeated-invocation scenarios;
     - run focused/targeted tests and adjacent tests when required
   - Do **not** mark the task complete (`- [ ]` → `- [x]`) if its mandatory tests fail
   - Mark task complete only after required implementation and mandatory focused tests succeed
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
   - If all done: follow **Post-apply next-step recommend** in `.cursor/commands/opsx-apply.md` (do not claim archive readiness)
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

Implementation tasks complete.

If production Python changed (`app/**/*.py` or top-level production scripts):
  Next: `/opsx-pyright-strict-coverage base=<BASE>`
  Then: `/opsx-external-call-coverage base=<BASE>` (after pyright PASS)
  Then: `/opsx-static-check` (after external-call PASS, focus=all)
  Then: `/opsx-verify <change-name>`
Else:
  Next: `/opsx-verify <change-name>`

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

**Guardrails**
- Keep going through tasks until done or blocked
- Always read `.cursor/commands/opsx-apply.md` before implementation
- Always read `.cursor/rules/testing-rules.mdc` before implementation
- Always read context files before starting (from the apply instructions output)
- Follow Architecture Decision Lookup from `/opsx-apply`, not a local conflicting copy
- Stop with `NO_GO` when planned placement conflicts with an accepted architecture decision
- Read `TEST_COVERAGE_PACKET` when present; absence does not block legacy apply
- Packet status alone does not block implementation and does not equal verify/archive verdict
- Never mark `[x]` when mandatory tests for that task fail
- Do not invent mandatory scenarios without evidence
- Do not create phantom fields or impossible states; do not fully mock the causal boundary under test
- Do not declare final adequacy or archive readiness
- After completion / `all_done`, follow Post-apply next-step recommend in `/opsx-apply` (`/opsx-pyright-strict-coverage` then `/opsx-external-call-coverage` when production `.py` changed, else `/opsx-verify <change-name>`)
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
