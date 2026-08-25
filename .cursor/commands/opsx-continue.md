---
name: /opsx-continue
id: opsx-continue
category: Workflow
description: Continue working on a change - create the next artifact (Experimental)
---

Continue working on a change by creating the next artifact.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**OpenSpec guard:** Before this command writes artifacts, run `poetry run python tools/openspec/openspec_guard.py --scenario opsx_continue --strict`. Stop on non-zero exit and report the guard output.

**Input**: Optionally specify a change name after `/opsx-continue` (e.g., `/opsx-continue add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`. When the change name is known, use `openspec status/instructions --change "<name>"` and canonical change paths; do not inventory unrelated changes; do not gate on unconditional `git status`.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes sorted by most recently modified. Then use the **AskUserQuestion tool** to let the user select which change to work on.

   Present the top 3-4 most recently modified changes as options, showing:
   - Change name
   - Schema (from `schema` field if present, otherwise "spec-driven")
   - Status (e.g., "0/5 tasks", "complete", "no tasks")
   - How recently it was modified (from `lastModified` field)

   Mark the most recently modified change as "(Recommended)" since it's likely what the user wants to continue.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check current status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand current state. The response includes:
   - `schemaName`: The workflow schema being used (e.g., "spec-driven")
   - `artifacts`: Array of artifacts with their status ("done", "ready", "blocked")
   - `isComplete`: Boolean indicating if all artifacts are complete
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repo-local paths.

3. **Act based on status**:

   ---

   **If all artifacts are complete (`isComplete: true`)**:
   - Congratulate the user
   - Show final status including the schema used
   - Suggest: "All artifacts created! You can now implement this change with `/opsx:apply` or archive it with `/opsx:archive`."
   - STOP

   ---

   **If artifacts are ready to create** (status shows artifacts with `status: "ready"`):
   - Pick the FIRST artifact with `status: "ready"` from the status output
   - Get its instructions:
     ```bash
     openspec instructions <artifact-id> --change "<name>" --json
     ```
   - Parse the JSON. The key fields are:
     - `context`: Project background (constraints for you - do NOT include in output)
     - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
     - `template`: The structure to use for your output file
     - `instruction`: Schema-specific guidance
     - `resolvedOutputPath`: Resolved path or pattern to write the artifact
     - `dependencies`: Completed artifacts to read for context
   - **Create the artifact file**:
     - Read any completed dependency files for context
     - Use `template` as the structure - fill in its sections
     - Apply `context` and `rules` as constraints when writing - but do NOT copy them into the file
     - Write to the `resolvedOutputPath` specified in instructions. If it is a glob pattern, choose the concrete file path using the schema instruction and the change's context
   - Show what was created and what's now unlocked
   - STOP after creating ONE artifact

   ---

   **If no artifacts are ready (all blocked)**:
   - This shouldn't happen with a valid schema
   - Show status and suggest checking for issues

4. **After creating an artifact, show progress**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After each invocation, show:
- Which artifact was created
- Schema workflow being used
- Current progress (N/M complete)
- What artifacts are now unlocked
- Prompt: "Run `/opsx-continue` to create the next artifact"

**Artifact Creation Guidelines**

The artifact types and their purpose depend on the schema. Use the `instruction` field from the instructions output to understand what to create.

Common artifact patterns:

**spec-driven schema** (proposal → specs → design → tasks):
- **proposal.md**: Ask user about the change if not clear. Fill in Why, What Changes, Capabilities, Impact.
  - The Capabilities section is critical - each capability listed will need a spec file.
- **specs/<capability>/spec.md**: Create one spec per capability listed in the proposal's Capabilities section (use the capability name, not the change name).
- **design.md**: Document technical decisions, architecture, and implementation
  approach **only after** `DESIGN_READINESS` passes (see **Design Generation**
  below). Resolve SoT/ownership/write-path/recovery before READY; never defer
  those to apply. When the Change has temporal/stateful behavior, also emit a
  **Derived Lifecycle** section (see below) — planning representation only,
  not a new Owner authority. Preserve upstream MUST / MUST NOT / MAY.
- **tasks.md**: Break down implementation into checkboxed tasks **only after**
  `TASK_GENERATION_READINESS` passes (see **Task Generation** below).
  `tasks.md` implements already-resolved design — it MUST NOT complete
  unresolved architecture/SoT/ownership/write-path/semantic choices.
- After a Derived Lifecycle exists in design, each **specs/<capability>/spec.md**
  MUST cover every materially observable lifecycle transition with a requirement/
  scenario, or record an explicit proof that a separate scenario is not needed.
  Spec MUST NOT invent behavior absent from lifecycle / reviewed Owner Contract.

For other schemas, follow the `instruction` field from the CLI output.

### Design Generation (design.md — shared with `/opsx-ff`)

**Authority:** `.cursor/pipeline/contracts/DESIGN_GENERATION.md` (SoT).
`/opsx-continue` and `/opsx-ff` MUST produce semantically equivalent designs
from the same upstream context (advancement mode differs only).

When the ready artifact is `design` (or you are about to write `design.md`):

1. Read dependency artifacts (owner-contract, proposal, specs, decisions) and
   relevant repository evidence / architecture decisions (context-first).
2. Build an in-memory **draft** `design.md` (do not declare complete yet).
3. Run full `DESIGN_READINESS` from the contract **after** draft
   construction (technical resolution + post-generation
   `NORMATIVE_PRESERVATION_CHECK`):

```text
DESIGN_READINESS
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes | not_applicable
DURABLE_SOT_RESOLVED: yes | not_applicable
WRITE_AUTHORITY_RESOLVED: yes | not_applicable
RECOVERY_SEMANTICS_RESOLVED: yes | not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
```

4. Technical architecture choices (PG vs Redis, existing vs new state,
   owner component, write authority, recovery) MUST be resolved in design
   from evidence + decisions, with WHAT/WHO/WHERE/WHO-writes/HOW-recover +
   rationale. Owner confirm is not required when WHAT/SCOPE/ACCEPTANCE are
   unchanged. Forbidden: «выбрать в apply», «PG/Redis — apply-time»,
   READY + deferred architecture.

5. If a required technical choice cannot be safely resolved:

```text
DESIGN_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
UNRESOLVED: <exact choice>
EVIDENCE_MISSING: <gap>
FILES_CHANGED: none
```

Do **not** mark design complete. Do **not** invent apply-time authority.

6. Preserve normative modality from authoritative upstream:
   `MUST→MUST`, `MUST NOT→MUST NOT`, `MAY→MAY`.
   Forbidden: `MUST→MAY`, `MUST→SHOULD`, `MUST NOT→SHOULD NOT`.
   Upstream modality conflict →
   `DESIGN_STATUS: BLOCKED` / `REASON: UPSTREAM_NORMATIVE_CONFLICT`.
   Draft-introduced drift →
   `NORMATIVE_MODALITY_PRESERVED: no` /
   `REASON: NORMATIVE_MODALITY_DRIFT` (do not declare complete).

7. `Open Questions` may list only harmless naming (enum/field/helper) after
   authority/semantics are fixed. Implementation-critical questions
   (SoT, ownership, write authority, epoch/recovery semantics) → BLOCKED.

8. For temporal/stateful Changes, also apply **Derived Lifecycle** below.
   Lifecycle DERIVED does not waive technical-choice or modality rules.

9. Only then write/complete `design.md` with `DESIGN_STATUS: READY`
   (`NORMATIVE_MODALITY_PRESERVED: yes` required).

### Task Generation (tasks.md — shared with `/opsx-ff`)

**Authority:** `.cursor/pipeline/contracts/TASK_GENERATION.md` (SoT).
`/opsx-continue` and `/opsx-ff` MUST produce semantically equivalent tasks
from the same upstream artifacts.

When the ready artifact is `tasks` (or you are about to write `tasks.md`):

1. Read dependency artifacts (design, specs, decisions, owner-contract as
   applicable).
2. Build an in-memory **draft** `tasks.md` (do not write yet).
3. Run full `TASK_GENERATION_READINESS` from the contract **after** draft
   construction (pre-draft upstream scan + post-generation
   `NORMATIVE_PRESERVATION_CHECK`):

```text
TASK_GENERATION_READINESS
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes | not_required
SCENARIO_PLAN_EVIDENCE_ID: <id> | not_required
SCENARIO_PLAN_STATUS: ready | not_required
SCENARIO_PLAN_FRESHNESS: current | not_required
TASKS_STATUS: READY
```

When scenario coverage is required, `SCENARIO_REQUIREMENTS_CONSUMED: yes`
requires a CURRENT durable receipt at
`openspec/changes/<change>/scenario-coverage/plan.receipt.json`
(see `TASK_GENERATION.md` §6 / `SCENARIO_TEST_COVERAGE.md`
DURABLE_PLAN_EVIDENCE). Chat-only plan is insufficient.

```text
TASKS_STATUS: BLOCKED
REASON: SCENARIO_PLAN_EVIDENCE_MISSING | SCENARIO_PLAN_EVIDENCE_STALE |
  SCENARIO_PLAN_EVIDENCE_INTEGRITY_FAIL
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
FILES_CHANGED: none
```

4. If any unresolved technical design choice would become an implementer
   task («выбрать SoT», «PG или Redis», ownership, write-path, architecture,
   semantic behavior) and upstream does not resolve it:

```text
TASKS_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
FILES_CHANGED: none
```

Return the exact unresolved item + artifact to fix. Do **not** ask Owner
automatically (technical design gap ≠ Owner semantic gap). Do **not** write
`tasks.md`.

5. Evidence roles when behavior intentionally changes:
   `LEGACY_BASELINE` | `TARGET_REGRESSION` | `FINAL_ACCEPTANCE`.
   Forbidden: require old characterization assertions to stay green after
   the intentional semantic change; forbidden plan contradiction
   OLD MUST / OLD MUST NOT.

6. Preserve normative modality and conditional branches from upstream:
   `MUST→MUST`, `MUST NOT→MUST NOT`, `MAY→MAY`.
   Forbidden: `MUST→MAY`, `MUST NOT→SHOULD NOT`, or other weakening;
   forbidden collapsing `IF X → MUST A; ELSE → MUST NOT A` into `A MAY`.
   Upstream modality conflict →
   `TASKS_STATUS: BLOCKED` / `REASON: UPSTREAM_NORMATIVE_CONFLICT`.
   Draft-introduced drift →
   `NORMATIVE_MODALITY_PRESERVED: no` /
   `REASON: NORMATIVE_MODALITY_DRIFT` (do not write).
   When epoch semantics exist: new epoch only after **actual** Auto start.

7. Only then write `tasks.md` with `TASKS_STATUS: READY`
   (`NORMATIVE_MODALITY_PRESERVED: yes` and
   `CONDITIONAL_BRANCHES_PRESERVED: yes` required).

### Derived Lifecycle (design — temporal / stateful Changes)

Authority model:

```text
owner-contract.md (+ owner-contract-review PASS) = semantic authority
design Lifecycle                               = DERIVED planning representation
continue / ff                                  = no product authority
```

When creating `design.md` for a Change with temporal/stateful behavior:

1. Derive a minimal ordered Lifecycle (`L1..Ln`) from, in order:
   - reviewed `openspec/changes/<change>/owner-contract.md`;
   - accepted/proposed decisions for this change;
   - repository facts;
   - already-created planning artifacts (proposal/specs/decisions).
2. Step count is **not** fixed to 3–7 — use the shortest sequence sufficient
   for this Change. Non-temporal / simple Changes: do **not** invent a
   ceremonial lifecycle.
3. Each step MUST carry local provenance, e.g.:
   `SOURCE: owner-contract.md / decision D-003 / repository fact`.
4. Record status:
   - `LIFECYCLE_STATUS: DERIVED` when every material transition is uniquely
     determined by reviewed Owner semantics (do **not** ask Owner to
     re-confirm via `CONFIRM_LIFECYCLE` / parallel Owner gate).
5. If after A the Owner Contract leaves B|C unresolved → **stop** writing
   further planning that depends on that fork:

```text
LIFECYCLE_STATUS: UNRESOLVED
UNRESOLVED_TRANSITION: <exact fork>
SOURCE_GAP: <what Owner Contract / decision lacks>
NEXT_ACTION: /opsx-owner-contract-review change=<change>
```

Do **not** invent semantic transitions. Do **not** create `CONFIRM_LIFECYCLE`
or a second Owner confirmation contour inside continue.
`DERIVED` may restructure already-authorized semantics in time; it MUST NOT
add product semantics.

Example Lifecycle skeleton (illustrative — adapt to the Change):

```text
## Lifecycle

LIFECYCLE_STATUS: DERIVED

L1. Entry / gate
SOURCE: owner-contract.md / …

L2. Active operation
SOURCE: …

L3. Trigger / terminal condition
SOURCE: …

L4. State transition / side effect
SOURCE: …

L5. Waiting / paused behavior
SOURCE: …

L6. Recovery / clear condition
SOURCE: …

L7. Conditional resume / next epoch
SOURCE: …
```

**Guardrails**
- Create ONE artifact per invocation
- Always read dependency artifacts before creating a new one
- Never skip artifacts or create out of order
- If context is unclear, ask the user before creating
- Verify the artifact file exists after writing before marking progress
- Use the schema's artifact sequence, don't assume specific artifact names
- For temporal Changes: design MUST include Derived Lifecycle with provenance
  when behavior is temporal/stateful; unresolved forks → owner-contract-review
  (not `CONFIRM_LIFECYCLE`)
- Before writing/completing `design.md`: follow
  `.cursor/pipeline/contracts/DESIGN_GENERATION.md`
  (draft → post-generation `NORMATIVE_PRESERVATION_CHECK`;
  `NORMATIVE_MODALITY_PRESERVED: yes` required for READY); on BLOCKED do not
  declare design complete (never defer SoT/ownership/write-path to apply;
  preserve MUST)
- Before writing `tasks.md`: follow `.cursor/pipeline/contracts/TASK_GENERATION.md`
  (draft → post-generation `NORMATIVE_PRESERVATION_CHECK`;
  `NORMATIVE_MODALITY_PRESERVED` + `CONDITIONAL_BRANCHES_PRESERVED` required
  for READY); on BLOCKED leave `FILES_CHANGED: none`
  (do not create tasks that complete design)
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output
