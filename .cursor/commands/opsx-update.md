---
name: /opsx-update
id: opsx-update
category: Workflow
description: Update a change - revise existing planning artifacts and keep them coherent (Experimental)
---

Revise a change's existing planning artifacts and keep them coherent. Never edit code.

**Bound-scope front-door:** If the user wants to cut an oversized change TZ / set an MVP boundary **and** park the deferred remainder into `DOTO/WORKLOG.md`, do **not** invent that dual-write here. Redirect to `/opsx-bound-scope` (plan → `:GO`). There is **no** `/opsx-update:split` — now/later analysis while thinking is `/opsx-explore` (`NOW_LATER`); durable park is `/opsx-bound-scope`. After `/opsx-bound-scope:GO`, this command **consumes** the emitted `UPDATE_HANDOFF` as a specific revision request (confirm-before-write still applies; never recreate deferred units as owed tasks **unless** the owner passes the Deferred re-entry gate below). Coherence-only edits without WORKLOG park stay on `/opsx-update`.

**Deferred park / re-entry boundary (with `/opsx-bound-scope`):**

| Action | Owner command |
|---|---|
| Cut current change + append `[deferred-from:<CHANGE_ID>]` to WORKLOG | `/opsx-bound-scope:GO` |
| Apply KEEP narrowing from `UPDATE_HANDOFF` | `/opsx-update` (this command) |
| Warn that ideas were parked for later | `/opsx-update` (mandatory check) |
| Pull a parked idea back into **current** change scope | `/opsx-update` only after explicit owner `REENTER_CONFIRMED` |

`/opsx-update` MUST treat `[deferred-from:<CHANGE_ID>]` (and matching titles/notes for this change) as **out of current owed DoD** until the owner explicitly confirms re-entry. Silent re-inflation of a bounded change is forbidden.

**Planning-review repair front-door:** When the user pastes or references a
`PLANNING_REVIEW_HANDOFF` with `MODE: REPAIR_PLANNING_PACKAGE` (and/or
`TARGET_WRITER: /opsx-update`), treat that handoff as the authoritative
repair request for this invocation. Handoff field names and repair semantics
are defined in `.cursor/pipeline/contracts/PLANNING_REVIEW.md` (producer:
`/opsx-planning-review`). Confirm-before-write still applies.

Algorithm:

1. Validate handoff: `CHANGE_ID`, `FINDINGS`, `FIRST_BAD_ARTIFACT`,
   `EXPECTED_SEMANTICS`, `DO_NOT_CHANGE`, `WRITE_BOUNDARY`.
2. Repair `FIRST_BAD_ARTIFACT` first using `EXPECTED_SEMANTICS` / per-finding
   `REPAIR_REQUIRED` — do not invent product decisions or expand scope.
3. Then repair/regenerate only `AFFECTED_DOWNSTREAM` / stale derivatives;
   do not modify unaffected upstream.
4. Do **not** edit `owner-contract.md` unless the finding explicitly routes
   Owner-contract repair via `/opsx-owner-contract-review` + `/opsx-new`
   (out of this mode).
5. Forbidden: production code, apply, new product decisions, scope expansion
   beyond the handoff.
6. After successful repair, soft-recommend
   `/opsx-planning-review change=<id>` (not `/opsx-apply`) until that review
   returns `STATUS: PASS`.

Keep `UPDATE_HANDOFF` / coherence / bug-episode paths unchanged when no
planning-review handoff is present.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**OpenSpec guard:** Before this command writes artifacts, run `poetry run python tools/openspec/openspec_guard.py --scenario opsx_update --strict`. Stop on non-zero exit and report the guard output.

**Architecture Decision Lookup:** When revising artifacts, resolve `artifactPaths.decisions.existingOutputPaths` first, then only needed accepted decisions under `openspec/decisions/`. Follow `.cursor/commands/opsx-source-resolution.md`; do not rediscover the selected change by scanning all changes. Reconcile specs/design/tasks/decisions with relevant decisions. If a new fact changes architecture ownership, layering, write-path placement, or a reusable domain invariant, update or create a proposed `decisions/<slug>/decision.md` artifact under the change root using `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied.

**Semantic write-target preflight:** Follow
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. When revising a high-risk
write and repository evidence exposes multiple plausible entities/legs/adapters,
artifacts MUST durably name `TARGET_ENTITY_OR_LEG`, `ALLOWED_ADAPTERS`,
`FORBIDDEN_ADAPTERS`, evidence, Owner decision source, and paired
positive/negative tests in an **explicit SWT schema block** (exact field
names). Architecture Decision `## Allowed` / `## Forbidden` prose and design
Ownership tables **alone** are **not** MEANING_LOCK `RESOLVED`
(`prose≠RESOLVED`) — do **not** mark the package coherent / apply-ready until
the schema block exists. Chat-only Owner answers are insufficient: materialize
them into planning artifacts before recommending `/opsx-apply`. If evidence does
not select one target, return `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` and ask the
contract's single concrete Owner question. Never infer product semantics from
similar names. Competing legs MUST NOT be closed with SEMANTIC
`NOT_APPLICABLE`.

**Product Acceptance preflight:** Follow
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. When revising planning,
record/update `PRODUCT_ACCEPTANCE_REQUIRED`. If required, keep MEANING_LOCK
durable via the explicit SWT schema tokens above (prose alone = missing). For temporal/stateful Changes with reviewed `owner-contract.md`:
write or refresh durable Derived Lifecycle in `design.md`
(`LIFECYCLE_STATUS: DERIVED`, per-step SOURCE) from Owner Contract +
decisions + repo facts — **do not** re-ask Owner `CONFIRM_LIFECYCLE` when
unambiguous. Unresolved material forks →
`/opsx-owner-contract-review` (not a parallel confirm contour). Legacy
Changes without owner-contract may still use `OWNER_LIFECYCLE_ECHO` +
`CONFIRM_LIFECYCLE` (or `CORRECT` → rewrite → confirm). Keep lifecycle↔
scenario coverage on the path (`/opsx-spec-scenario-coverage mode=plan`
then later audit/certify). Soft tooling waivers never substitute for
Product Acceptance. Chat-only lifecycle is not durable.

**Design Generation gate (when revising `design.md`):** Follow
`.cursor/pipeline/contracts/DESIGN_GENERATION.md` (same SoT as
`/opsx-continue` / `/opsx-ff`). Before treating a revised `design.md` as
coherent / complete:

1. Run `DESIGN_READINESS` (SoT/ownership/write/recovery resolved or
   `not_applicable`; normative conflicts none; no implementation-critical
   Open Questions).
2. Resolve technical architecture from repository evidence + decisions, or
   stop with `DESIGN_STATUS: BLOCKED` /
   `REASON: TECHNICAL_DESIGN_UNRESOLVED` (or `UPSTREAM_NORMATIVE_CONFLICT`).
3. Preserve upstream `MUST` / `MUST NOT` / `MAY` (no `MUST→MAY` weakening).
4. Forbidden: «выбрать в apply», «PG/Redis — apply-time», READY design with
   architecture deferred to implementation.

Lifecycle DERIVED does **not** waive this gate.

**Input**: Optionally specify a change name after `/opsx-update` (e.g., `/opsx-update add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

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

2b. **Deferred park check (mandatory when WORKLOG exists)**

   Read `DOTO/WORKLOG.md` if present (path from `openspec/policies/EXPLORE_POLICY.md` → `explore.worklog.path`; default `DOTO/WORKLOG.md`). Missing WORKLOG is not a blocker: record `DEFERRED_PARKS: none_found (WORKLOG missing)` and continue.

   Collect open parks for **this** change:

   - lines / blocks tagged `[deferred-from:<CHANGE_ID>]` where `<CHANGE_ID>` matches the selected change;
   - ignore entries already marked `[re-entered:<CHANGE_ID>]` or clearly struck as done.

   Always emit (even on pure coherence / UPDATE_HANDOFF KEEP-narrowing):

   ```text
   DEFERRED_PARKS_FOR_CHANGE:
   - <title or one-line> — source/notes summary
   (or: none_found)
   ```

   If parks exist, include a short warning:

   ```text
   DEFERRED_WARNING:
   These ideas were parked out of the current change (via /opsx-bound-scope).
   They are NOT owed DoD unless you explicitly re-enter them.
   ```

   Compare the **requested revision** (user ask, pasted handoff, or coherence edit that would add scope) against `DEFERRED_PARKS_FOR_CHANGE`:

   - Overlap / would re-add a parked unit into proposal/design/tasks/specs → **stop before write** and emit:

   ```text
   DEFERRED_REENTRY_REQUIRED:
   UNIT: <parked title>
   WHY_MATCHED: <short>
   QUESTION: Confirm you want to pull this idea out of WORKLOG back into the current change scope?
   Reply: REENTER_CONFIRMED <unit> | KEEP_DEFERRED <unit>
   ```

   - Without `REENTER_CONFIRMED` for that unit: MUST NOT write the re-entry into artifacts.
   - `KEEP_DEFERRED` / silence: leave artifacts without that unit; keep WORKLOG park as-is.
   - On `REENTER_CONFIRMED`: may add the unit to the change (still confirm-before-write per artifact), then **annotate** the matching WORKLOG park append-only / in-place mark as `[re-entered:<CHANGE_ID>]` (narrow WORKLOG write only — do not rewrite unrelated inbox lines; do not delete park history). Prefer adding a one-line note under the park rather than deleting it.
   - Consuming `UPDATE_HANDOFF` that only **removes/narrows** to KEEP MUST NOT treat deferred parks as re-entry; still print `DEFERRED_PARKS_FOR_CHANGE` as situational awareness.

3. **Understand the request**
   - If the user pasted or referenced a `PLANNING_REVIEW_HANDOFF` with
     `MODE: REPAIR_PLANNING_PACKAGE`, treat that as the authoritative repair
     request (see **Planning-review repair front-door** above). Do not mix
     with bound-scope KEEP/DEFER unless the handoff explicitly allows.
   - If the user pasted or referenced an `/opsx-bound-scope` `UPDATE_HANDOFF`, treat that as the authoritative KEEP revision request for this invocation (apply KEEP / remove-or-narrow deferred units; do not re-park WORKLOG — bound-scope already did). Do not re-add DEFER units from that handoff.
   - If the user asked for a specific revision ("the design now uses X"), that is the starting edit — run it through the Deferred re-entry gate in 2b when it overlaps parks.
   - If they only said "update" / "make this coherent", treat it as a coherence review: read the existing artifacts and check them against each other for contradictions, gaps, and duplication. Coherence MUST NOT silently restore parked scope; if coherence “wants” a deferred unit back, use `DEFERRED_REENTRY_REQUIRED`.
   - If the request is clearly "bound scope + write WORKLOG" without a completed bound-scope GO, stop and point to `/opsx-bound-scope`.

4. **Perform Architecture Decision Lookup**

   - Resolve `artifactPaths.decisions.existingOutputPaths` first, then only needed accepted decisions.
   - Further `openspec/decisions/` lookup only for remaining gaps (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Never dump the full tree.
   - If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing artifacts. Budget exhaustion is not proof that no decision exists; do **not** emit `Architecture Decision Missing`.
   - Read existing proposed decisions from `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the artifacts touch ownership, layering, write paths, or domain invariants and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision, output `Architecture Decision Missing`.
   - Include the decision registry and proposed decisions in the coherence check alongside specs/design/tasks.

5. **Read and reconcile**
   - Read the artifact(s) the request touches and the change's other existing artifacts.
   - Apply the requested edit. Then check every other existing artifact against it - in ANY direction: an edit to a later artifact may require revising an earlier one, not only the other way around. Build order is a useful reading order, not a constraint on which artifacts may be revised.
   - Note everything that is now inconsistent, missing, or contradictory.
   - If a revision introduces or changes reusable architecture ownership, update/create a proposed decision under `decisions/<slug>/decision.md` before treating the artifacts as coherent. Get `openspec instructions decisions --change "<name>" --json` first and follow `rules.decisions`.
   - Revise only files that already exist (`existingOutputPaths`). Do NOT create change artifacts that don't exist yet, and do NOT invent new files under a glob artifact - note them and point the user to `/opsx-continue` to create them. Exception: proposed architecture decisions may be created under the change's `decisions/` artifact when required by Architecture Decision Lookup.
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
- `DEFERRED_PARKS_FOR_CHANGE` / any `DEFERRED_REENTRY_REQUIRED` outcomes
- Which artifacts were revised (and which proposed revisions were rejected)
- Anything deferred to `/opsx-continue` (not-yet-created artifacts or files)
- WORKLOG annotations made on confirmed re-entry (if any)
- Where the change stands and the recommended next command



## Bug-episode routing (when case=/finding= present)

Authority: `.cursor/pipeline/ORCHESTRATION_MVP.md` §0.1–0.2 +
`.cursor/pipeline/contracts/bug-episode/TASK_DELTA.md` +
`.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

When the request includes `case=<CASE_ID>` and/or `finding=<FINDING_ID>`,
or otherwise continues a durable bug episode, this command is the
**immediate process step** for Route B. It is **not** production GO and does
**not** replace `/opsx-apply` or `/opsx-fix-bug` as implementation executor.

Route B layers (do not collapse):

```text
CLASSIFICATION ROUTE:           ROUTE_B
IMMEDIATE PROCESS STEP:         /opsx-update
IMPLEMENTATION EXECUTION ROUTE: PENDING_UNTIL_TASK_DELTA
  (chosen only after TASK_DELTA)
```

Preserve Route B meaning:

```text
SPEC_BUG | SPEC_GAP → /opsx-update → TASK_DELTA
TASK_DELTA: CHANGED   → EXPECTED_EXECUTION_ROUTE: /opsx-apply
TASK_DELTA: UNCHANGED → EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
```

```text
/opsx-update ≠ production implementation
/opsx-update ≠ Owner production GO
/opsx-update ≠ EXPECTED_EXECUTION_ROUTE
TASK_DELTA ≠ Owner GO
```

After TASK_DELTA, both `/opsx-apply` and `/opsx-fix-bug` still require:

```text
RED → Owner GO → production write → GREEN
```

### C1 — Hard classify-first / Route B gate (before any OpenSpec write)

Before **any** OpenSpec planning write, TASK_DELTA write, or route-state
mutation on a bug episode, read durable classification evidence from:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md  → ## ROUTE_STATE
```

Required durable receipt (all must hold; do **not** silently infer missing
fields from classification alone):

```text
CLASSIFICATION: SPEC_BUG | SPEC_GAP
CHOSEN_ROUTE: ROUTE_B
EXPECTED_NEXT_COMMAND: /opsx-update
```

Equivalent process-state acceptance (when next-command field is present via
route state even if older packets omit the literal key):

```text
CURRENT_ROUTE_STATE: AWAITING_SPEC_UPDATE
```

still requires `CLASSIFICATION` ∈ {`SPEC_BUG`,`SPEC_GAP`} **and**
`CHOSEN_ROUTE: ROUTE_B`. Missing `CHOSEN_ROUTE` with only `SPEC_BUG` →
blocked (P5), not inferred.

Do **not** require:

```text
EXPECTED_EXECUTION_ROUTE: /opsx-update
```

Implementation executor is unknown until TASK_DELTA.
`EXPECTED_EXECUTION_ROUTE` on a valid pre-update Route B receipt is
`PENDING_UNTIL_TASK_DELTA` (or still `PENDING` on legacy packets that have
not yet migrated the literal token).

Do **not** accept free-form user/executor claims («это spec bug», chat
paraphrase, Mini-lesson) as a substitute for durable classification.

### C3 — Missing classification

If classification receipt is absent / incomplete:

```text
STATUS: blocked_needs_classify_first
SPEC_WRITE_ALLOWED: NO
TASK_DELTA_WRITE_ALLOWED: NO
PRODUCTION_WRITE_ALLOWED: NO
```

Hard stop. Pasteable next:

```text
/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
```

Do not edit OpenSpec. Do not write TASK_DELTA evidence. Do not invent
classification or `CHOSEN_ROUTE`.

### C2 / C4 — Wrong classification or wrong route

If durable `CURRENT_CLASSIFICATION` / latest classify event is one of:

```text
IMPLEMENTATION_BUG
FALSE_POSITIVE
OUT_OF_SCOPE
```

**or** `CHOSEN_ROUTE` is present and `!= ROUTE_B`
**or** `EXPECTED_NEXT_COMMAND` is present and `!= /opsx-update`
(while classification claims Route B inconsistently):

then `/opsx-update` MUST NOT continue Route B.

```text
STATUS: BLOCKED_ROUTE_MISMATCH
SPEC_WRITE_ALLOWED: NO
TASK_DELTA_WRITE_ALLOWED: NO
PRODUCTION_GO_ALLOWED: NO
EPISODE_CLOSE_ALLOWED: NO
```

Append one ROUTE-TRACE event (SCHEMA_VERSION 2) with **next-command**
mismatch fields — do **not** store `/opsx-update` as an implementation
execution route:

```text
ACTUAL_NEXT_COMMAND: /opsx-update
NEXT_COMMAND_RECONCILIATION: MISMATCH
EXPECTED_EXECUTION_ROUTE: <unchanged; still pending / route-implied>
ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
RECONCILIATION_REASON: update_invoked_without_ROUTE_B_handoff
TERMINAL_STATUS: BLOCKED_ROUTE_MISMATCH
```

Refresh LEDGER `## ROUTE_STATE` snapshot only; never rewrite prior JSONL.

### Canonical LEDGER field names (new writes)

**Write only** these canonical fields into `## ROUTE_STATE` / TASK_DELTA /
route events:

```text
TASK_DELTA: CHANGED | UNCHANGED
CHOSEN_ROUTE
EXPECTED_NEXT_COMMAND
ACTUAL_NEXT_COMMAND
NEXT_COMMAND_RECONCILIATION
EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION
CURRENT_ROUTE_STATE
CURRENT_CLASSIFICATION
LAST_ROUTE_EVENT_ID
LAST_ROUTE_EVENT_SEQUENCE
LAST_ROUTE_EVENT_AT
CURRENT_ACTOR_ROLE
CURRENT_ACTOR_AGENT_ID
CURRENT_ACTOR_CHAT_ID
OWNER_GATE_STATUS
TERMINAL_STATUS
NEXT_ACTION
ROUTE_TRACE_PATH
```

**Legacy read-only** (may be read for compatibility; MUST NOT be written in
new artifacts):

```text
TASK_DELTA_STATUS
CURRENT_ROUTE
IMPLEMENTATION_ROUTE
TASK_DELTA_DETECTED
```

Legacy map when reading old packets only:

```text
TASK_DELTA_DETECTED: YES → CHANGED
TASK_DELTA_DETECTED: NO  → UNCHANGED
IMPLEMENTATION_ROUTE     → EXPECTED_EXECUTION_ROUTE
CURRENT_ROUTE            → CURRENT_ROUTE_STATE (best-effort)
```

### C5 — Allowed flow after Route B gate pass

1. Revise OpenSpec planning artifacts only (never production code).
2. After confirmed writes (or explicit no-op coherence), compute durable
   `TASK_DELTA` evidence under:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/TASK-DELTA-<FINDING_ID>.md
```

3. After TASK_DELTA:

```text
If TASK_DELTA: CHANGED:
  EXPECTED_EXECUTION_ROUTE: /opsx-apply
  ACTUAL_EXECUTION_ROUTE: PENDING
  ROUTE_RECONCILIATION: PENDING
  EXPECTED_NEXT_COMMAND: /opsx-apply
  CURRENT_ROUTE_STATE: AWAITING_APPLY_RED

If TASK_DELTA: UNCHANGED:
  EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
  ACTUAL_EXECUTION_ROUTE: PENDING
  ROUTE_RECONCILIATION: PENDING
  EXPECTED_NEXT_COMMAND: /opsx-fix-bug
  CURRENT_ROUTE_STATE: AWAITING_FIX_BUG_RED
```

4. Append ROUTE-TRACE events for `update` and `task_delta_decision`
   (append-only; no rewrite). Update LEDGER `## ROUTE_STATE` with
   **canonical** field names only.
5. Do **not** auto-run `/opsx-apply`. `TASK_DELTA: CHANGED` is never
   automatic production permission — apply still needs RED + Owner GO.
6. Never write `EXPECTED_EXECUTION_ROUTE=/opsx-update` or
   `ACTUAL_EXECUTION_ROUTE=/opsx-update`.
7. **Close / handback intent** (authority:
   `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`):
   - Optional arg `close_finding=auto_after_green|ask_after_green|never`
     and/or `post_green_owner=bug-team|solo`.
   - Defaults when omitted: `ask_after_green` + `POST_GREEN_OWNER=bug-team`.
   - Persist on LEDGER `## ROUTE_STATE` + TASK-DELTA evidence:
     `CLOSE_FINDING_INTENT`, `POST_GREEN_OWNER`, `HANDBACK_COMMAND`
     (`/opsx-bug-team case=<CASE_ID> mode=continue` pre-GREEN;
     `mode=resume-family-fanout` when family path after root GREEN).
   - **Never** write `closed_fixed` / close the finding from update.
8. Bug-episode output MUST include soft recommends (not silent return):
   - **PRIMARY** `NEXT_ACTION`: after CHANGED → `/opsx-apply … case= finding=`
     (still needs RED+GO); after UNCHANGED → `/opsx-fix-bug …` (not apply).
   - **SECONDARY**: pasteable `HANDBACK_COMMAND` when Owner wants team
     to resume later.
   - **ALSO_OK**: solo walk through apply/fix-bug (advisory; not a violation).

### Required bug-episode output (complete TASK_DELTA)

After a successful bug-episode `/opsx-update` (or blocked gate outcomes
above), return exactly these fields when a TASK_DELTA decision was
reached; on classify-first / mismatch blockers, omit TASK_DELTA body and
emit `STATUS` + pasteable next instead:

```text
STATUS: ok | blocked_needs_classify_first | BLOCKED_ROUTE_MISMATCH

CASE_ID:
FINDING_ID:
BASELINE_TASKS_REF:

SPEC_FILES_CHANGED:
TASK_FILES_INSPECTED:

TASKS_BEFORE:
TASKS_AFTER:

NEW_TASKS:
CHANGED_TASKS:
REMOVED_TASKS:

TASK_DELTA: CHANGED | UNCHANGED

TASK_DELTA_EVIDENCE_PATH:

EXPECTED_NEXT_COMMAND: /opsx-apply | /opsx-fix-bug
EXPECTED_EXECUTION_ROUTE: /opsx-apply | /opsx-fix-bug
CURRENT_ROUTE_STATE: AWAITING_APPLY_RED | AWAITING_FIX_BUG_RED

ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
ROUTE_TRACE_PATH:
CLOSE_FINDING_INTENT:
POST_GREEN_OWNER:
HANDBACK_COMMAND:
NEXT_ACTION:
ALSO_OK:

ROUTE_TRANSITION:
  (schema: .cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md)
  FROM_STATE: AWAITING_SPEC_UPDATE | <prior>
  RESULT: TASK_DELTA_CHANGED | TASK_DELTA_UNCHANGED
  TO_STATE: AWAITING_APPLY_RED | AWAITING_FIX_BUG_RED
  NEXT_COMMAND: /opsx-apply | /opsx-fix-bug
  NEXT_ARGS: WITHOUT GO   # GO is Owner-later; RED still required
  PRECONDITIONS:
    GO_TOKEN: FORBIDDEN
    RED_REQUIRED: yes
  REQUIRED_EVIDENCE: TASK_DELTA_EVIDENCE_PATH
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
```

Rules for `/opsx-update` as worker envelope:

* `EXPECTED_EXECUTION_ROUTE` / `ACTUAL_EXECUTION_ROUTE` MUST NEVER be
  `/opsx-update` (update is process step only).
* `MISSION_COMPLETE: no` always on this worker.
* `FINDING_TERMINAL: no` unless a separate terminal disposition is already
  proven (update alone does not close a finding).
* Blockers (`blocked_needs_classify_first` / `BLOCKED_ROUTE_MISMATCH`):
  `RECOVERY_CLASS: BLOCKED | PAUSED`; no invented next route.

Also keep the normal OpenSpec update summary (artifacts revised / rejected /
deferred).

### Route-trace event (SCHEMA_VERSION 2)

On every significant bug-episode hop (including hard-stop blockers and
successful update / task_delta_decision), append **one** JSONL line to:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Required fields:

```text
SCHEMA_VERSION
EVENT_ID
EVENT_SEQUENCE
PREVIOUS_EVENT_ID

CASE_ID
FINDING_ID
EVENT_TYPE
COMMAND
COMMAND_MODE

ACTOR_ROLE
ACTOR_AGENT_ID
ACTOR_CHAT_ID

FROM_STATE
TO_STATE

CLASSIFICATION
CHOSEN_ROUTE
EXPECTED_NEXT_COMMAND
ACTUAL_NEXT_COMMAND
NEXT_COMMAND_RECONCILIATION

EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION
RECONCILIATION_REASON

TASK_DELTA
TASK_DELTA_EVIDENCE_PATH

STARTED_AT
COMPLETED_AT
DURATION_MS
TERMINAL_STATUS
```

Actor identity:

```text
ACTOR_AGENT_ID: CURRENT_CHAT_AGENT  # if no separate agent id
ACTOR_CHAT_ID:  durable stable chat label (required)
```

Never rewrite prior JSONL events. Snapshot LEDGER `## ROUTE_STATE` must
align with the latest applicable event.

**Guardrails**
- Planning artifacts only - NEVER edit implementation code. If the revised plan implies code changes, stop and point to `/opsx-apply`.
- Do not mark artifacts coherent while a high-risk multi-target write remains
  unresolved (`BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`); materialize Owner
  semantic answers into artifacts before recommending apply.
- Do not recommend apply-ready when `PRODUCT_ACCEPTANCE_REQUIRED=true` and
  MEANING_LOCK is missing/blocked, **or** Derived Lifecycle is
  missing/UNRESOLVED when temporal behavior applies under a reviewed Owner
  Contract, **or** (legacy path only) `OWNER_LIFECYCLE_ECHO` /
  `CONFIRM_LIFECYCLE` is missing; lifecycle plan is not optional under PA.
  Do not demand a second `CONFIRM_LIFECYCLE` when `LIFECYCLE_STATUS: DERIVED`
  uniquely follows from reviewed Owner Contract.
- When revising `design.md`: follow
  `.cursor/pipeline/contracts/DESIGN_GENERATION.md`; do not mark design
  coherent or recommend apply-ready if `DESIGN_STATUS: BLOCKED`, SoT/
  ownership/write-path is deferred to apply, or MUST/MUST NOT was weakened.
- Do not mark artifacts coherent if implementation placement conflicts with an accepted decision or if required architecture placement is unresolved.
- Use the artifact ids and paths reported by `openspec status`; never branch on hardcoded artifact names.
- Edit only the concrete files in `existingOutputPaths`; never write to a glob `resolvedOutputPath`.
- Do not advance the change artifact build frontier: no new change artifacts, no new files under glob artifacts - that is `/opsx-continue`'s job. Proposed decisions under the change's optional `decisions/` artifact are the only exception.
- Confirm every edit with the user before writing.
- Deferred parks: always surface `DEFERRED_PARKS_FOR_CHANGE` when WORKLOG exists; never silently restore `[deferred-from:<CHANGE_ID>]` into owed DoD; re-entry requires `REENTER_CONFIRMED`; the only allowed WORKLOG write from this command is annotating confirmed re-entry (`[re-entered:<CHANGE_ID>]`). Parking new deferrals remains `/opsx-bound-scope:GO` only.
- If the request changes the change's *intent* rather than refining it, recommend starting fresh with `/opsx-new` (the "Update vs. Start Fresh" heuristic).
- Bug-episode: never write OpenSpec / TASK_DELTA without durable Route B receipt (`CLASSIFICATION` + `CHOSEN_ROUTE=ROUTE_B` + `EXPECTED_NEXT_COMMAND=/opsx-update` or `CURRENT_ROUTE_STATE=AWAITING_SPEC_UPDATE`); never store `/opsx-update` as `EXPECTED_EXECUTION_ROUTE` / `ACTUAL_EXECUTION_ROUTE`; never write legacy `TASK_DELTA_STATUS` / `CURRENT_ROUTE` in new artifacts.
