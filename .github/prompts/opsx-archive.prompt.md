---
description: Archive a completed change in the experimental workflow
---

Archive a completed change in the experimental workflow.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Before archiving, search `openspec/decisions/**/*.md` and read proposed decisions from `artifactPaths.decisions.existingOutputPaths`. Use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied. Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving the change into `changes/archive` when they are reusable architecture source of truth. If there is nothing reusable to promote, explicitly output `Reusable architecture promotions: none`. Do not archive when `design.md` contains a permanent architecture decision that has not been moved to `openspec/decisions/` or a proposed decision artifact.

**Input**: Optionally specify a change name after `/opsx-archive` (e.g., `/opsx-archive add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

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

   **Compliance axis (required non-task):** `proposal`, `design`, `specs`.
   For each, require `artifacts[id].status == "done"`.

   The `decisions` artifact is optional. If `artifactPaths.decisions.existingOutputPaths` is empty and Architecture Decision Lookup does not require a proposed decision, do not count `decisions` as incomplete. If proposed decision files already exist under the change, require that artifact `done` (or treat missing acceptance as incomplete planning).

   **Tasks are NOT on this axis.** Absence of `tasks.md` / `tasks` not `done` is **not** a planning compliance failure and must **not** block a full archive.

   **If any of proposal | design | specs has status != `done`:**
   - This is a planning defect (косяк), not soft confirmation territory
   - Emit `ARCHIVE_BLOCKED_INCOMPLETE_PLANNING` (see Output)
   - Stop. Do **not** `mv`. Do **not** accept `yes` / `ok` / `да` / free-form continue
   - Do **not** accept `CONTINUE_ARCHIVE_INCOMPLETE` for missing proposal/design/specs
   - Next: `/opsx-ff` | `/opsx-continue` | `/opsx-update` (разобраться), then re-run archive

   **If proposal | design | specs are all `done`:** planning compliance OK → continue to step 3

3. **Check task completion status**

   Read the tasks file when `artifactPaths.tasks.existingOutputPaths` is non-empty.

   **If no tasks file / empty `existingOutputPaths`:**
   - Full archive path remains valid (spec-only / docs-capture allowed)
   - Optional one-line note only: `Tasks: none (allowed)`
   - Do **not** warn as incomplete; do **not** require a confirm token

   **If tasks.md exists:** count `- [ ]` (incomplete) vs `- [x]` (complete).

   **If any `- [ ]` found:**
   - Emit `ARCHIVE_WAITING_CONFIRM_OPEN_TASKS` (see Output)
   - Stop until the user message contains the exact token `CONTINUE_ARCHIVE_INCOMPLETE`
   - Refuse free-form `yes` / `ok` / `да` / `продолжай` without that token
   - After the token: proceed (sync / ADL / mv); note open-task override in summary

   **If all checkboxes are `[x]`:** proceed

4. **Assess delta spec sync state**

   Use `artifactPaths.specs.existingOutputPaths` from status JSON to check for delta specs. If none exist, proceed without sync prompt.

   **If delta specs exist:**
   - Compare each delta spec with its corresponding main spec at `openspec/specs/<capability>/spec.md`
   - Determine what changes would be applied (adds, modifications, removals, renames)
   - Show a combined summary before prompting

   **Prompt options:**
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, use Task tool (subagent_type: "general-purpose", prompt: "Use Skill tool to invoke openspec-sync-specs for change '<name>'. Delta spec analysis: <include the analyzed delta spec summary>"). Proceed to archive regardless of choice.

5. **Perform Architecture Decision Archive Gate**

   - Resolve decision paths context-first (`artifactPaths.decisions` / user paths / index); further `openspec/decisions/` lookup only for remaining gaps (budget ? 3 unless `EVIDENCE_GAP`). Never dump the full tree.
   - Read proposed decisions from `artifactPaths.decisions.existingOutputPaths`, if any.
   - Get `openspec instructions decisions --change "<name>" --json` when proposed decisions exist or archive analysis requires a proposed decision, and apply `rules.decisions`.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving `changeRoot` when they should become reusable source of truth; report promoted paths.
   - If the design contains permanent ownership, layering, write-path, or domain-invariant decisions that are not captured in `openspec/decisions/` or a proposed decision artifact, return `NO_GO` and do not archive.
   - If no proposed decision needs promotion, output `Reusable architecture promotions: none` and proceed.

6. **Perform the archive**

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

7. **Display summary**

   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Spec sync status (synced / sync skipped / no delta specs)
   - Tasks line: `none (allowed)` | `N/N complete` | `overridden open tasks via CONTINUE_ARCHIVE_INCOMPLETE`

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs
**Tasks:** none (allowed) | <n>/<n> complete

Planning compliance OK (proposal|design|specs done).

### Soft next (optional — not an archive gate)
If client/CS distribution materials are needed:
`/opsx-distribute-brief change=<change-name>`
```

**Output On Success (No Delta Specs)**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** No delta specs
**Tasks:** none (allowed) | <n>/<n> complete

Planning compliance OK (proposal|design|specs done).

### Soft next (optional — not an archive gate)
If client/CS distribution materials are needed:
`/opsx-distribute-brief change=<change-name>`
```

**Output On Success (Sync Skipped / Open-Tasks Override)**

```
## Archive Complete (with notes)

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** Sync skipped (user chose to skip) | ✓ Synced | No delta specs
**Tasks:** overridden open checkboxes via CONTINUE_ARCHIVE_INCOMPLETE | …

Planning compliance OK (proposal|design|specs done). Missing tasks.md is never a warning.

### Soft next (optional — not an archive gate)
If client/CS distribution materials are needed:
`/opsx-distribute-brief change=<change-name>`
```

**Output On Blocked (Incomplete Planning)**

```
## Archive Blocked (incomplete planning)

**Change:** <change-name>
**Reason:** proposal|design|specs status != done (косяк — разобраться; not a soft confirm)
**Incomplete:** <artifact id=status, …>
**Tasks:** ignored for this gate (absence of tasks.md is allowed and is NOT listed here)

Do not archive. Do not accept free-form confirm or CONTINUE_ARCHIVE_INCOMPLETE for this tier.

**Next:**
/opsx-ff
# or /opsx-continue / /opsx-update — then re-run /opsx-archive <change-name>
```

**Output On Waiting (Open Task Checkboxes)**

```
## Archive Waiting Confirm (open tasks)

**Change:** <change-name>
**Open checkboxes:** <count> in tasks.md
**Planning:** proposal|design|specs done

To archive anyway, reply exactly:

CONTINUE_ARCHIVE_INCOMPLETE

(Free-form yes/ok/да is refused.)
```

**Output On Error (Archive Exists)**

```
## Archive Failed

**Change:** <change-name>
**Target:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/

Target archive directory already exists.

**Options:**
1. Rename the existing archive
2. Delete the existing archive if it's a duplicate
3. Wait until a different date to archive
```

**Guardrails**
- Always prompt for change selection if not provided
- Do not archive if reusable architecture decisions remain only in design.md
- Explicitly report `Reusable architecture promotions: none` when there is nothing to promote
- Use artifact graph (openspec status --json) for completion checking — mechanical predicates only (no agent vibes)
- Absence of tasks.md does **not** prevent a full archive; do not treat it as incomplete planning
- Missing proposal|design|specs → HARD_BLOCK (`ARCHIVE_BLOCKED_INCOMPLETE_PLANNING`); no soft override token
- Open `- [ ]` in an existing tasks.md → stop until exact `CONTINUE_ARCHIVE_INCOMPLETE`
- Preserve .openspec.yaml when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, use the Skill tool to invoke `openspec-sync-specs` (agent-driven)
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
- Soft-suggest `/opsx-distribute-brief` after success when client/CS materials may be needed; never require it as an archive gate; never write the distribution brief from this command
