---
name: /opsx-archive
id: opsx-archive
category: Workflow
description: Archive a completed change in the experimental workflow
---

Archive a completed change in the experimental workflow.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Before archiving, resolve proposed decision paths from `artifactPaths.decisions.existingOutputPaths` first, then read only needed accepted decisions. Prefer exact paths over a full `openspec/decisions/**` walk. Follow `.cursor/commands/opsx-source-resolution.md`. Use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied. Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving the change into `changes/archive` when they are reusable architecture source of truth. If there is nothing reusable to promote, explicitly output `Reusable architecture promotions: none`. Do not archive when `design.md` contains a permanent architecture decision that has not been moved to `openspec/decisions/` or a proposed decision artifact.

**Semantic write-target hard stop:** Follow
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. For a high-risk
multi-target write, archive requires a durable explicit target
(`TARGET_ENTITY_OR_LEG`, `ALLOWED_ADAPTERS`, `FORBIDDEN_ADAPTERS`) in
artifacts/decision. `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` or missing explicit
destructive target is a **hard stop** — do not sync, promote decisions, or move
the change. This is not an overridable warning.

**Product Acceptance hard stop:** Follow
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. Archive requires
`PRODUCT_ACCEPTANCE_STATUS=PASS` or `NOT_REQUIRED` from the archive verify.
When `PRODUCT_ACCEPTANCE_REQUIRED=true`, `FAIL` / `BLOCKED` / missing PA is a
**hard stop** — soft tooling waives do not clear it. Do not sync, promote, or
move the change.

**Verify-phase hard stop:** Follow
`.cursor/pipeline/contracts/VERIFY_PHASES.md`. Archive requires a recent
`/opsx-verify mode=archive` with final marker `✅ GO` for this change.
`✅ IMPL_OK` / `mode=impl` alone **never** authorizes archive. If the latest
verify in-session was `mode=impl` only, or only `IMPL_OK`/`IMPL_GAPS` markers
are present without archive `✅ GO`:

```text
STATUS: BLOCKED_NEEDS_ARCHIVE_VERIFY
NEXT_ACTION: /opsx-verify mode=archive <change-name>
DO_NOT_DO_YET: sync / decision promote / archive move
```

**Input**: Optionally specify a change name after `/opsx-archive` (e.g., `/opsx-archive add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

0. **Archive-verify gate (before other steps that mutate planning home)**

   Confirm in-session (or Owner-supplied) evidence of
   `/opsx-verify mode=archive` → `✅ GO` for `<change>`. If missing → stop with
   `BLOCKED_NEEDS_ARCHIVE_VERIFY` and the NEXT_ACTION above.

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show only active changes (not already archived).
   Include the schema used for each change if available.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check artifact completion status**

   Run `openspec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context
   - `artifacts`: List of artifacts with their status (`done` or other)

   The `decisions` artifact is optional. If `artifactPaths.decisions.existingOutputPaths` is empty and Architecture Decision Lookup does not require a proposed decision, do not count `decisions` as an incomplete artifact.

   **If any non-optional artifacts are not `done`:**
   - Display warning listing incomplete artifacts
   - Prompt user for confirmation to continue
   - Proceed if user confirms

3. **Check task completion status**

   Read the tasks file (typically `tasks.md`) to check for incomplete tasks.

   Count tasks marked with `- [ ]` (incomplete) vs `- [x]` (complete).

   **If incomplete tasks found:**
   - Display warning showing count of incomplete tasks
   - Prompt user for confirmation to continue
   - Proceed if user confirms

   **If no tasks file exists:** Proceed without task-related warning.

4. **Semantic write-target archive gate (hard stop)**

   Follow `.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md` **before** sync,
   decision promotion, or archive move:
   - high-risk multi-target write without durable
     `TARGET_ENTITY_OR_LEG` / `ALLOWED_ADAPTERS` / `FORBIDDEN_ADAPTERS` →
     `NO_GO` / `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`; stop;
   - do **not** treat this as a confirmable warning;
   - route Owner to `/opsx-update` for durable materialization.

4a. **Product Acceptance archive gate (hard stop)**

   Follow `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` **before** sync,
   decision promotion, or archive move:
   - require archive-verify evidence of `PRODUCT_ACCEPTANCE_STATUS=PASS` or
     `NOT_REQUIRED`;
   - if `PRODUCT_ACCEPTANCE_REQUIRED=true` and status is not PASS → stop with
     `product_acceptance_not_pass` (include fail pillar when known);
   - soft ECC/pyright/static Owner waives do **not** clear this gate;
   - route MEANING → `/opsx-update`; LIFECYCLE missing/unconfirmed
     `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` → `/opsx-update` (or
     `/opsx-ff`); LIFECYCLE scenario report / unmapped rows →
     `/opsx-spec-scenario-coverage`; SIDE_EFFECT → `/opsx-test` /
     apply test materialization — then `/opsx-verify mode=archive`.

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

   - Resolve proposed decision paths from `artifactPaths.decisions.existingOutputPaths` first.
   - Read only needed accepted decisions (index → exact paths; bounded fallback ≤ 3 targeted lookups if gaps remain unless `EVIDENCE_GAP` is recorded). Never dump `openspec/decisions/**`.
   - If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without archiving. Budget exhaustion is not proof that no decision exists; do **not** emit `Architecture Decision Missing`.
   - Read proposed decisions from `artifactPaths.decisions.existingOutputPaths`, if any.
   - Get `openspec instructions decisions --change "<name>" --json` when proposed decisions exist or archive analysis requires a proposed decision, and apply `rules.decisions`.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - Promote accepted proposed decisions from `openspec/changes/<change>/decisions/` into `openspec/decisions/` before moving `changeRoot` when they should become reusable source of truth; report promoted paths.
   - If the design contains permanent ownership, layering, write-path, or domain-invariant decisions and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes they are not captured in `openspec/decisions/` or a proposed decision artifact, output `Architecture Decision Missing`, return `NO_GO`, and do not archive.
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
   - Spec sync status (synced / sync skipped / no delta specs)
   - Note about any warnings (incomplete artifacts/tasks)

**Output On Success**

```
## Archive Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** ✓ Synced to main specs

All artifacts complete. All tasks complete.

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

All artifacts complete. All tasks complete.

### Soft next (optional — not an archive gate)
If client/CS distribution materials are needed:
`/opsx-distribute-brief change=<change-name>`
```

**Output On Success With Warnings**

```
## Archive Complete (with warnings)

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** the archive path derived from `planningHome.changesDir`/YYYY-MM-DD-<name>/
**Specs:** Sync skipped (user chose to skip)

**Warnings:**
- Archived with 2 incomplete artifacts
- Archived with 3 incomplete tasks
- Delta spec sync was skipped (user chose to skip)

Review the archive if this was not intentional.

### Soft next (optional — not an archive gate)
If client/CS distribution materials are needed:
`/opsx-distribute-brief change=<change-name>`
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
- Do not archive, sync, or promote decisions when a high-risk multi-target write
  lacks a durable semantic write target (`unresolved_semantic_write_target` /
  `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`) — hard stop, not a warning
- Explicitly report `Reusable architecture promotions: none` when there is nothing to promote
- Use artifact graph (openspec status --json) for completion checking
- Don't block archive on warnings - just inform and confirm
- Preserve .openspec.yaml when moving to archive (it moves with the directory)
- Show clear summary of what happened
- If sync is requested, use the Skill tool to invoke `openspec-sync-specs` (agent-driven)
- If delta specs exist, always run the sync assessment and show the combined summary before prompting
- Soft-suggest `/opsx-distribute-brief` after success when client/CS materials may be needed; never require it as an archive gate; never write the distribution brief from this command
