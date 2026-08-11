---
name: /opsx-ff
id: opsx-ff
category: Workflow
description: Create a change and generate all artifacts needed for implementation in one go
---

Fast-forward through artifact creation - generate everything needed to start implementation.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**OpenSpec guard:** Before this command writes artifacts, run `poetry run python tools/openspec/openspec_guard.py --scenario opsx_ff --strict`. Stop on non-zero exit and report the guard output.

**Input**: The argument after `/opsx:ff` is the change name (kebab-case), OR a description of what the user wants to build.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md` for any supplied exact change/decision paths; do not rediscover known artifacts via full-tree inventory.

**Semantic write-target preflight:** Follow
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. When the change plans a
high-risk write and repository evidence exposes multiple plausible
entities/legs/adapters, artifacts MUST durably name `TARGET_ENTITY_OR_LEG`,
`ALLOWED_ADAPTERS`, `FORBIDDEN_ADAPTERS`, evidence, Owner decision source, and
paired positive/negative tests. If evidence does not select one target, return
`BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`, ask the contract's single concrete
Owner question, and do not declare the change apply-ready. Never infer product
semantics from similar names.

**Steps**

1. **If no input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```
   This creates a scaffolded change in the planning home resolved by the CLI.

3. **Get the artifact build order**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: array of artifact IDs needed before implementation (e.g., `["tasks"]`)
   - `artifacts`: list of all artifacts with their status and dependencies
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repo-local paths.

4. **Create artifacts in sequence until apply-ready**

   Use the **TodoWrite tool** to track progress through the artifacts.

   Loop through artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact that is `ready` (dependencies satisfied)**:
      - Get instructions:
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - The instructions JSON includes:
        - `context`: Project background (constraints for you - do NOT include in output)
        - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
        - `template`: The structure to use for your output file
        - `instruction`: Schema-specific guidance for this artifact type
        - `resolvedOutputPath`: Resolved path or pattern to write the artifact
        - `dependencies`: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using `template` as the structure and write it to `resolvedOutputPath`
      - Apply `context` and `rules` as constraints - but do NOT copy them into the file
      - Show brief progress: "✓ Created <artifact-id>"

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `openspec status --change "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"` in the artifacts array
      - Stop when all `applyRequires` artifacts are done

   c. **If an artifact requires user input** (unclear context):
      - Use **AskUserQuestion tool** to clarify
      - Then continue with creation

5. **Confirm semantic write target**

   Before declaring apply readiness, evaluate the shared semantic-target
   contract against completed artifacts:
   - `NOT_APPLICABLE` — continue only when justified (single proven target);
     competing legs/adapters MUST NOT use `NOT_APPLICABLE`;
   - `RESOLVED` — confirm all required fields are materialized;
   - `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` — stop and route the durable
     answer back through planning; chat-only selection is insufficient.

6. **Product Acceptance (kernel DONE path)**

   Follow `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` before
   apply-ready:
   - Decide and record `PRODUCT_ACCEPTANCE_REQUIRED`.
   - When required: MEANING_LOCK must be durable.
   - **Derived Lifecycle (same rules as `/opsx-continue`):** for temporal/
     stateful Changes, design MUST include a durable Lifecycle section with
     `LIFECYCLE_STATUS: DERIVED` and per-step `SOURCE:` provenance, derived
     from reviewed `owner-contract.md` + decisions + repo facts + prior
     planning artifacts. Do **not** invent semantics. Step count is not
     fixed to 3–7.
   - When Lifecycle is uniquely determined by reviewed Owner Contract →
     **do not** require a second Owner `CONFIRM_LIFECYCLE`. Authority remains
     the reviewed Owner Contract.
   - If a material transition is A|B with no Owner resolution → stop with
     `LIFECYCLE_STATUS: UNRESOLVED` and
     `NEXT_ACTION: /opsx-owner-contract-review change=<name>` (not a parallel
     confirm contour inside ff).
   - **Legacy fallback only:** Changes without reviewed `owner-contract.md`
     may still use durable `OWNER_LIFECYCLE_ECHO` + Owner `CONFIRM_LIFECYCLE`
     (or `CORRECT` → rewrite → confirm).
   - Schedule `/opsx-spec-scenario-coverage mode=plan` (lifecycle↔scenario
     coverage; not optional under PA); note SIDE_EFFECT_PROOF obligations.
   - Do not declare apply-ready if PA required and MEANING_LOCK is missing
     or blocked, **or** (for reviewed-contract Changes) Derived Lifecycle is
     missing/UNRESOLVED when temporal behavior applies, **or** (legacy path
     only) `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` is missing.
     Chat-only lifecycle is not durable.
   - Invariant vs continue: same Owner Contract + same repository state →
     semantically equivalent lifecycle/design/spec whether built via
     sequential `/opsx-continue` or `/opsx-ff` (advancement mode differs only).

7. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Run `/opsx:apply` to start implementing."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `openspec instructions` for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file - fill in its sections
- When creating `design.md` for temporal/stateful behavior: apply the same
  Derived Lifecycle rules as `/opsx-continue` (`LIFECYCLE_STATUS: DERIVED`,
  per-step SOURCE, no invented transitions, UNRESOLVED → owner-contract-review).
  Specs MUST cover material lifecycle transitions (or explicit not-needed proof).
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, ask if user wants to continue it or create a new one
- Verify each artifact file exists after writing before proceeding to next
