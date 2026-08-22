---
name: openspec-archive-change
description: Archive a completed change in the experimental workflow. Use when the user wants to finalize and archive a change after implementation is complete.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.6.0"
---

Archive a completed change in the experimental workflow.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Before archiving, search `openspec/decisions/**/*.md` and read proposed decisions from `artifactPaths.decisions.existingOutputPaths`. Use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied. Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving the change into `changes/archive` when they are reusable architecture source of truth. If there is nothing reusable to promote, explicitly output `Reusable architecture promotions: none`. Do not archive when `design.md` contains a permanent architecture decision that has not been moved to `openspec/decisions/` or a proposed decision artifact.

**Semantic write-target authority:** Read and follow
`.cursor/commands/opsx-archive.md` and
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. Unresolved high-risk
multi-target writes are a hard stop before sync, decision promotion, and archive
move — not an overridable warning.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check planning compliance (mechanical — status JSON only)**

   Run `openspec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context
   - `artifacts`: List of artifacts with their status (`done` or other)

   **Compliance axis (required non-task):** `proposal`, `design`, `specs` must each have `status == "done"`.

   The `decisions` artifact is optional. If `artifactPaths.decisions.existingOutputPaths` is empty and Architecture Decision Lookup does not require a proposed decision, do not count `decisions` as incomplete. If proposed decision files already exist, require that artifact `done`.

   **Tasks are NOT on this axis.** Absence of `tasks.md` does **not** block a full archive.

   **If any of proposal | design | specs has status != `done`:**
   - Emit `ARCHIVE_BLOCKED_INCOMPLETE_PLANNING`; stop; do not `mv`
   - No free-form confirm; no `CONTINUE_ARCHIVE_INCOMPLETE` for this tier
   - Next: `/opsx-ff` | `/opsx-continue` | `/opsx-update`, then re-run archive

   **If proposal | design | specs are all `done`:** continue to step 3

3. **Check task completion status**

   **If no tasks file / empty `artifactPaths.tasks.existingOutputPaths`:**
   - Proceed (full archive); optional note `Tasks: none (allowed)`

   **If tasks.md exists:** count `- [ ]` vs `- [x]`.

   **If any `- [ ]`:**
   - Emit `ARCHIVE_WAITING_CONFIRM_OPEN_TASKS`; stop until exact token `CONTINUE_ARCHIVE_INCOMPLETE`
   - Refuse free-form yes/ok/да

   **If all `[x]`:** proceed

4. **Semantic write-target archive gate (hard stop)**

   Follow `.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md` and
   `.cursor/commands/opsx-archive.md` **before** sync, decision promotion, or
   archive move. Unresolved high-risk multi-target write → `NO_GO` /
   `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`; not a confirmable warning.

5. **Assess delta spec sync state**

   Use `artifactPaths.specs.existingOutputPaths` from status JSON to check for delta specs. If none exist, proceed without sync prompt.

   **If delta specs exist:**
   - Compare each delta spec with its corresponding main spec at `openspec/specs/<capability>/spec.md`
   - Determine what changes would be applied (adds, modifications, removals, renames)
   - Show a combined summary before prompting

   **Prompt options:**
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, use Task tool (subagent_type: "general-purpose", prompt: "Use Skill tool to invoke openspec-sync-specs for change '<name>'. Delta spec analysis: <include the analyzed delta spec summary>"). Proceed to archive regardless of choice.

6. **Perform Architecture Decision Archive Gate**

   - Resolve decision paths context-first (`artifactPaths.decisions` / user paths / index); further `openspec/decisions/` lookup only for remaining gaps (budget ≤ 3 unless `EVIDENCE_GAP`). Never dump the full tree.
   - Read proposed decisions from `artifactPaths.decisions.existingOutputPaths`, if any.
   - Get `openspec instructions decisions --change "<name>" --json` when proposed decisions exist or archive analysis requires a proposed decision, and apply `rules.decisions`.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving `changeRoot` when they should become reusable source of truth; report promoted paths.
   - If the design contains permanent ownership, layering, write-path, or domain-invariant decisions that are not captured in `openspec/decisions/` or a proposed decision artifact, return `NO_GO` and do not archive.
   - If no proposed decision needs promotion, output `Reusable architecture promotions: none` and proceed.

7. **Perform the archive**

   Create an `archive` directory under `planningHome.changesDir` if it doesn't exist:
   ```bash
   mkdir -p "<planningHome.changesDir>/archive"
   ```

   Generate target name using current date: `YYYY-MM-DD-<change-name>`

   **Check if target already exists:**
   - If yes: Fail with error, suggest renaming existing archive or using different date
   - If no: Move `changeRoot` to the archive directory

   ```bash
   mv "<changeRoot>" "<planningHome.changesDir>/archive/YYYY-MM-DD-<name>"
   ```

8. **Display summary**

   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Whether specs were synced (if applicable)
   - Tasks: `none (allowed)` | `N/N complete` | open-task override via token

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs (or "No delta specs" or "Sync skipped")
**Tasks:** none (allowed) | <n>/<n> complete

Planning compliance OK (proposal|design|specs done).
```

**Output On Blocked (Incomplete Planning)**

```
## Archive Blocked (incomplete planning)

**Change:** <change-name>
**Reason:** proposal|design|specs status != done
**Incomplete:** <artifact id=status, …>

Do not archive. Next: /opsx-ff | /opsx-continue | /opsx-update
```

**Output On Waiting (Open Task Checkboxes)**

```
## Archive Waiting Confirm (open tasks)

**Change:** <change-name>
**Open checkboxes:** <count>

Reply exactly: CONTINUE_ARCHIVE_INCOMPLETE
```

**Guardrails**
- Always prompt for change selection if not provided
- Do not archive if reusable architecture decisions remain only in design.md
- Do not archive, sync, or promote decisions when a high-risk multi-target write
  lacks a durable semantic write target — hard stop, not a warning
- Explicitly report `Reusable architecture promotions: none` when there is nothing to promote
- Use artifact graph (openspec status --json) for completion checking — mechanical predicates only
- Absence of tasks.md does **not** prevent a full archive
- Missing proposal|design|specs → HARD_BLOCK; no soft override
- Open `- [ ]` in existing tasks.md → exact `CONTINUE_ARCHIVE_INCOMPLETE` only
- Preserve .openspec.yaml when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, use openspec-sync-specs approach (agent-driven)
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
