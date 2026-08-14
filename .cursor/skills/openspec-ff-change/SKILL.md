---
name: openspec-ff-change
description: Fast-forward through OpenSpec artifact creation. Use when the user wants to quickly create all artifacts needed for implementation without stepping through each one individually.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.6.0"
---

Fast-forward through artifact creation - generate everything needed to start implementation in one go.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Semantic write-target authority:** Read and follow
`.cursor/commands/opsx-ff.md` and
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. For high-risk
multi-target writes, do not declare apply readiness until artifacts explicitly
materialize the target, allowed/forbidden adapters, evidence and paired tests.
Unresolved choice returns `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`; never guess.

**Input**: The user's request should include a change name (kebab-case) OR a description of what they want to build.

**Steps**

1. **If no clear input provided, ask what they want to build**

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
      - **If the artifact is `design`:** follow
        `.cursor/pipeline/contracts/DESIGN_GENERATION.md` first. Build draft,
        then run `DESIGN_READINESS` (post-generation
        `NORMATIVE_PRESERVATION_CHECK`). Resolve SoT/ownership/write/recovery
        or BLOCK (`TECHNICAL_DESIGN_UNRESOLVED` /
        `UPSTREAM_NORMATIVE_CONFLICT` / `NORMATIVE_MODALITY_DRIFT`).
        Preserve MUST/MUST NOT. Never defer architecture to apply. On
        BLOCKED stop without declaring design complete. On READY
        (`NORMATIVE_MODALITY_PRESERVED: yes`), same design rules as
        `/opsx-continue`.
      - **If the artifact is `tasks`:** follow
        `.cursor/pipeline/contracts/TASK_GENERATION.md` first. Build draft,
        then run `TASK_GENERATION_READINESS` (post-generation
        `NORMATIVE_PRESERVATION_CHECK`). On BLOCKED stop without writing
        `tasks.md`. On READY (`NORMATIVE_MODALITY_PRESERVED: yes` and
        `CONDITIONAL_BRANCHES_PRESERVED: yes`), same evidence-role +
        modality + conditional-branch rules as `/opsx-continue`.
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

5. **Product Acceptance before apply-ready**

   Follow `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` (mirror
   `.cursor/commands/opsx-ff.md`):
   - Decide/record `PRODUCT_ACCEPTANCE_REQUIRED`.
   - When required: durable MEANING_LOCK; durable `OWNER_LIFECYCLE_ECHO`
     (3–7 temporal steps) in design/decision/spec; Owner
     `CONFIRM_LIFECYCLE` (or `CORRECT` → rewrite → confirm); schedule
     `/opsx-spec-scenario-coverage mode=plan` (must materialize durable
     `scenario-coverage/plan.md` + `plan.receipt.json`; chat-only insufficient).
   - Do **not** claim apply-ready / "Ready for implementation" if PA
     required and echo/`CONFIRM_LIFECYCLE` is missing (chat-only lifecycle
     is not durable).

6. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for planning review, then implementation."
  (only if PA gates above allow; otherwise BLOCKED awaiting
  `CONFIRM_LIFECYCLE` / MEANING_LOCK)
- Prompt: "Run `/opsx:apply` or ask me to implement to start working on the tasks."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `openspec instructions` for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file - fill in its sections
- When creating `design.md`: follow `.cursor/pipeline/contracts/DESIGN_GENERATION.md`
  (identical to `/opsx-continue`; draft → post-generation check; continue≡ff).
- When creating `tasks.md`: follow `.cursor/pipeline/contracts/TASK_GENERATION.md`
  (identical to `/opsx-continue`; draft → post-generation check; continue≡ff;
  CURRENT durable scenario-plan receipt required when scenarios apply).
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, suggest continuing that change instead
- Verify each artifact file exists after writing before proceeding to next
- Before writing/completing `design.md`: follow
  `.cursor/pipeline/contracts/DESIGN_GENERATION.md`
  (draft → post-generation check; `NORMATIVE_MODALITY_PRESERVED` required);
  on BLOCKED do not declare design complete
- Before writing `tasks.md`: follow `.cursor/pipeline/contracts/TASK_GENERATION.md`
  (draft → post-generation check; modality + conditional branches required);
  on BLOCKED leave `FILES_CHANGED: none`
- When `PRODUCT_ACCEPTANCE_REQUIRED=true`, never treat apply-ready as true
  without durable `OWNER_LIFECYCLE_ECHO` + `CONFIRM_LIFECYCLE`
