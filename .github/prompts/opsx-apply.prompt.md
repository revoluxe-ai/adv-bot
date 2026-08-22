---
description: Implement tasks from an OpenSpec change (Experimental)
---

Implement tasks from an OpenSpec change.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Before changing code, resolve decision paths context-first from change `contextFiles.decisions` / `artifactPaths.decisions.existingOutputPaths` (bounded fallback under `openspec/decisions/` only for remaining gaps, budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded; never dump the full tree). Do **not** equate budget exhaustion with “no decision exists”: if ownership / layering / write-path / domain-invariant gaps remain unresolved after that budget (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Use `Architecture Decision Missing` only when lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision. Implementation must cite relevant decisions in progress or completion notes. If planned code placement contradicts an accepted decision, stop before editing code and return `NO_GO` with the conflicting decision path. If placement depends on a proposed decision, use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied before deciding whether code can proceed. Passing tests are not sufficient if placement violates a decision.

**Input**: Optionally specify a change name (e.g., `/opsx-apply add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

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
   - If `state: "blocked"` (missing artifacts): show message, suggest using `/opsx-continue`
   - If `state: "all_done"`: congratulate, suggest archive
   - Otherwise: proceed to implementation

4. **Read context files**

   Read `contextFiles` paths under execution-preflight Read I/O budgets (prefer sequential; parallel max 2; section Read for large artifacts when only part is needed).
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks, and optional decisions when present
   - Other schemas: follow the contextFiles from CLI output

5. **Perform Architecture Decision Lookup**

   - Resolve decision paths context-first (`artifactPaths.decisions` / user paths / index); further `openspec/decisions/` lookup only for remaining gaps (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Never dump the full tree.
   - If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Budget exhaustion is not proof that no decision exists.
   - Read existing proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the change touches ownership, layering, write paths, or domain invariants and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision, output `Architecture Decision Missing` and pause unless the artifacts already include a proposed decision.
   - If a proposed decision is required or present, get `openspec instructions decisions --change "<name>" --json` and apply `rules.decisions` before evaluating placement.
   - Compare planned implementation placement against accepted/proposed decisions before editing code.
   - If placement conflicts with an accepted decision, return `NO_GO` and do not edit code.

6. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Dynamic instruction from CLI

7. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

8. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest archive
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

All tasks complete! You can archive this change with `/opsx-archive`.
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
- Always read context files before starting (from the apply instructions output)
- Always perform Architecture Decision Lookup before code edits
- Stop with `NO_GO` when the decision-lookup fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved
- Stop with `NO_GO` when planned placement conflicts with an accepted architecture decision
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
