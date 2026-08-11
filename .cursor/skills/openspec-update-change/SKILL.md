---
name: openspec-update-change
description: Update an OpenSpec change by revising its existing planning artifacts and keeping them coherent with one another. Use when the user wants to revise a change's plan, fold new decisions into it, or reconcile its artifacts after an edit. Never edits code.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.6.0"
---

Revise a change's existing planning artifacts and keep them coherent. Never edit code.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** When revising artifacts, also check `openspec/decisions/**/*.md` and `artifactPaths.decisions.existingOutputPaths`. Reconcile specs/design/tasks/decisions with relevant decisions. If a new fact changes architecture ownership, layering, write-path placement, or a reusable domain invariant, update or create a proposed `decisions/<slug>/decision.md` artifact under the change root using `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied.

**Semantic write-target authority:** Read and follow
`.cursor/commands/opsx-update.md` and
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. For high-risk
multi-target writes, revise artifacts until they durably name the target,
allowed/forbidden adapters, evidence and paired tests. Chat-only Owner answers
are insufficient; unresolved choice returns
`BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` and must not be marked apply-ready.

**Product Acceptance / change spirit:** Follow
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. When
`PRODUCT_ACCEPTANCE_REQUIRED=true`, revise planning until durable
`OWNER_LIFECYCLE_ECHO` (3–7 temporal steps) exists in design/decision/spec
and Owner has issued `CONFIRM_LIFECYCLE` (or `CORRECT` → rewrite → confirm).
Chat-only lifecycle is insufficient; do not mark apply-ready without it.
(Prefer Derived Lifecycle from reviewed owner-contract when that path applies —
mirror `.cursor/commands/opsx-update.md`.)

**Design Generation gate:** When revising `design.md`, follow
`.cursor/pipeline/contracts/DESIGN_GENERATION.md` (identical to
`/opsx-continue` / `/opsx-ff`). Run `DESIGN_READINESS`; resolve SoT/ownership/
write/recovery or `DESIGN_STATUS: BLOCKED`; preserve MUST/MUST NOT; never
defer architecture to apply. Do not mark design coherent while BLOCKED.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes sorted by most recently modified. Then use the **AskUserQuestion tool** to let the user select which change to update.

   Present the top 3-4 most recently modified changes as options, showing:
   - Change name
   - Schema (from `schema` field if present, otherwise "spec-driven")
   - Status (e.g., "0/5 tasks", "complete", "no tasks")
   - How recently it was modified (from `lastModified` field)

   Mark the most recently modified change as "(Recommended)" since it's likely what the user wants to update.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Get the change's artifacts**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand current state. The response includes:
   - `schemaName`: The workflow schema being used (e.g., "spec-driven")
   - `artifacts`: Array of artifacts with their status ("done", "ready", "blocked")
   - `isComplete`: Boolean indicating if all artifacts are complete
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repo-local paths.

   The artifact ids and paths come from the active schema - do NOT assume them, and do NOT branch on hardcoded artifact names. Custom schemas must work unchanged.

   The files to edit are `artifactPaths.<id>.existingOutputPaths` - the concrete files that exist on disk, already glob-expanded for glob artifacts (e.g. `specs/**/*.md`). Do NOT write to `resolvedOutputPath`: for a glob artifact it is still the glob pattern, not a real file.

3. **Understand the request**
   - If the user asked for a specific revision ("the design now uses X"), that is the starting edit.
   - If they only said "update" / "make this coherent", treat it as a coherence review: read the existing artifacts and check them against each other for contradictions, gaps, and duplication.

4. **Perform Architecture Decision Lookup**

   - Resolve decision paths context-first (`artifactPaths.decisions` / user paths / index); further `openspec/decisions/` lookup only for remaining gaps (budget ? 3 unless `EVIDENCE_GAP`). Never dump the full tree.
   - Read existing proposed decisions from `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the artifacts touch ownership, layering, write paths, or domain invariants with no relevant decision, output `Architecture Decision Missing`.
   - Include the decision registry and proposed decisions in the coherence check alongside specs/design/tasks.

5. **Read and reconcile**
   - Read the artifact(s) the request touches and the change's other existing artifacts.
   - Apply the requested edit. Then check every other existing artifact against it - in ANY direction: an edit to a later artifact may require revising an earlier one, not only the other way around. Build order is a useful reading order, not a constraint on which artifacts may be revised.
   - Note everything that is now inconsistent, missing, or contradictory.
   - If a revision introduces or changes reusable architecture ownership, update/create a proposed decision under `decisions/<slug>/decision.md` before treating the artifacts as coherent. Get `openspec instructions decisions --change "<name>" --json` first and follow `rules.decisions`.
   - Revise only files that already exist (`existingOutputPaths`). Do NOT create change artifacts that don't exist yet, and do NOT invent new files under a glob artifact - note them and point the user to `/opsx:continue` to create them. Exception: proposed architecture decisions may be created under the change's `decisions/` artifact when required by Architecture Decision Lookup.
   - If the change is already coherent, say so and make no edits.

6. **Confirm and apply, one artifact at a time**
   - Show each proposed revision and why. Write only after the user confirms.
   - If the user rejects a revision, do not write it - leave that artifact unchanged.
   - When a substantial rewrite is needed, get that artifact's rules and template first:
     ```bash
     openspec instructions <artifact-id> --change "<name>" --json
     ```

7. **Point to the next step (guidance only - NEVER act on it)**
   - Artifacts still missing -> suggest `/opsx:continue` to create them.
   - Change already implemented (tasks checked off / already applied) -> the code may no longer match the revised plan; suggest `/opsx:apply` to carry the delta into code.
   - Everything done and implemented -> suggest `/opsx:archive`.

**Output**

After each invocation, show:
- Which artifacts were revised (and which proposed revisions were rejected)
- Anything deferred to `/opsx:continue` (not-yet-created artifacts or files)
- Where the change stands and the recommended next command

**Guardrails**
- Planning artifacts only - NEVER edit implementation code. If the revised plan implies code changes, stop and point to `/opsx:apply`.
- Do not mark artifacts coherent while a high-risk multi-target write remains
  unresolved (`BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`); materialize Owner
  semantic answers into artifacts before recommending apply.
- Do not recommend apply-ready when `PRODUCT_ACCEPTANCE_REQUIRED=true` and
  `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` is missing.
- When revising `design.md`: follow
  `.cursor/pipeline/contracts/DESIGN_GENERATION.md`; do not mark design
  coherent if `DESIGN_STATUS: BLOCKED` or architecture is deferred to apply.
- Do not mark artifacts coherent if implementation placement conflicts with an accepted decision or if required architecture placement is unresolved.
- Use the artifact ids and paths reported by `openspec status`; never branch on hardcoded artifact names.
- Edit only the concrete files in `existingOutputPaths`; never write to a glob `resolvedOutputPath`.
- Do not advance the change artifact build frontier: no new change artifacts, no new files under glob artifacts - that is `/opsx:continue`'s job. Proposed decisions under the change's optional `decisions/` artifact are the only exception.
- Confirm every edit with the user before writing.
- If the request changes the change's *intent* rather than refining it, recommend starting fresh with `/opsx:new` (the "Update vs. Start Fresh" heuristic).
