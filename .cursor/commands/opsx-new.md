---
name: /opsx-new
id: opsx-new
category: Workflow
description: Start a new change using the experimental artifact workflow (OPSX)
---

Start a new change using the experimental artifact-driven approach.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: The argument after `/opsx:new` is the change name (kebab-case), OR a description of what the user wants to build.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md` when exact paths/IDs appear later in the workflow; this command creates a new change and should not inventory unrelated trees first.

**Optional Evolution handoff:** Read
`openspec/policies/EVOLUTION_POLICY.md`. If the user supplies an
`EVOLUTION_HANDOFF`, validate its exact `CARD_PATH` and carry
`STAR_ID`/`INCREMENT_ID`/Current Increment boundary and
`CONTRIBUTION_TO_NORTH_STAR` into the change context for `/opsx-continue`. Do
not create artifacts in this command. Without a handoff,
classify the change as `STANDALONE`, `LEGACY_UNLINKED`, `CANDIDATE`, or
`NOT_APPLICABLE`; absence of `STAR_ID` is not a blocker. For a new
capability-sized `CANDIDATE`, read `openspec/evolution/index.md` and show up to
three likely `Title (STAR_ID)` matches as a soft recommendation—never create or
merge a card silently.

**Steps**

1. **If no input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Determine the workflow schema**

   Use the default schema (omit `--schema`) unless the user explicitly requests a different workflow.

   **Use a different schema only if the user mentions:**
   - A specific schema name → use `--schema <name>`
   - "show workflows" or "what workflows" → run `openspec schemas --json` and let them choose

   **Otherwise**: Omit `--schema` to use the default.

3. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```
   Add `--schema <name>` only if the user requested a specific workflow.
   This creates a scaffolded change in the planning home resolved by the CLI.

4. **Show the artifact status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Use the returned `planningHome`, `changeRoot`, `artifactPaths`, and `nextSteps` instead of assuming repo-local paths.

5. **Get instructions for the first artifact**
   The first artifact depends on the schema. Check the status output to find the first artifact with status "ready".
   ```bash
   openspec instructions <first-artifact-id> --change "<name>"
   ```
   This outputs the template and context for creating the first artifact.

6. **Preserve evolution context (when linked)**
   - Emit the validated `EVOLUTION_HANDOFF` in the session handoff to
     `/opsx-continue`.
   - State that only `CURRENT_INCREMENT` is owed scope.
   - Preserve `CONTRIBUTION_TO_NORTH_STAR`; do not infer it from `STAR_ID`.
   - State that `FUTURE_INCREMENTS` are context and MUST NOT become tasks.

7. **STOP and wait for user direction**

**Output**

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Current status (0/N artifacts complete)
- Evolution link: `LINKED | STANDALONE | LEGACY_UNLINKED | CANDIDATE | NOT_APPLICABLE`
- For `LINKED`: `Title (STAR_ID)` and Current Increment
- The template for the first artifact
- Prompt: "Ready to create the first artifact? Run `/opsx:continue` or just describe what this change is about and I'll draft it."

**Guardrails**
- Do NOT create any artifacts yet - just show the instructions
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists, suggest using `/opsx:continue` instead
- Pass --schema if using a non-default workflow
- Never require a North Star for every change or migrate legacy changes
- Never broaden a linked Current Increment with Future Increments
