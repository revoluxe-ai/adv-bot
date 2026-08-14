---
description: Start a new change (CREATE) or repair owner-contract.md from OWNER_REVIEW_HANDOFF (REPAIR) — OPSX
---

Start a new change using the experimental artifact-driven approach, **or**
repair an existing Change's `owner-contract.md` from a valid
`OWNER_REVIEW_HANDOFF`.

Canonical: `.cursor/commands/opsx-new.md`.
Fixtures: `.cursor/commands/_fixtures/opsx-new-owner-contract-repair/`.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: The argument after `/opsx-new` is the change name (kebab-case), OR a description of what the user wants to build, **or** a pasteable `/opsx-new` + `OWNER_REVIEW_HANDOFF` block from `/opsx-owner-contract-review`.

## Mode detection (mandatory first)

```text
if input contains literal OWNER_REVIEW_HANDOFF
   AND MODE: REPAIR_EXISTING_OWNER_CONTRACT:
    → REPAIR MODE (skip CREATE steps)
else:
    → CREATE MODE
```

Do **not** enter REPAIR from vague NL without that literal trigger.
Accept OCR pasteable fields without renaming.

---

## REPAIR MODE

1. Parse handoff; resolve existing `openspec/changes/<CHANGE_ID>/owner-contract.md`.
2. Validate before write — else `PAUSE` / `FILES_CHANGED: none`:
   - `UNRESOLVED_SEMANTIC_CHOICE` (A/B or `OWNER_INPUT_REQUIRED: YES`)
   - `INVALID_REPAIR_BOUNDARY` (scope beyond owner-contract.md)
   - `INVALID_REPAIR_HANDOFF` (bad/missing shell or target)
3. Do **not** scaffold, recreate, touch schema artifacts, or emit OCR PASS.
4. Apply only `REPAIRS_REQUIRED`; preserve `DO_NOT_CHANGE`; idempotent re-paste OK.
5. Emit `OWNER_CONTRACT_REPAIR_RESULT` →
   `NEXT_ACTION: /opsx-owner-contract-review change=<CHANGE_ID>`.

---

## CREATE MODE

1. **If no input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

   If the Owner request is substantially ambiguous about the desired result, ask the same existing open-ended clarification question before scaffolding. Do not invent product decisions or silently expand scope. Do not create a new clarification framework.

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

   If a change with that name already exists (and no REPAIR handoff) → stop and
   suggest `/opsx-continue` instead. Do not recreate scaffold. Do not silently REPAIR.

4. **Create Owner Contract (companion file — not a schema artifact)**

   Immediately after a successful scaffold, write
   `<changeRoot>/owner-contract.md` from the Owner request and available
   change context.

   This file is a **human-facing companion** for Owner review. It is **not**
   registered in the OpenSpec schema, **not** part of `openspec status`
   artifact sequence, and **must not** be copied into `spec` or treated as
   canonical authority for specs/design/tasks.

   **Semantic source priority (OWNER_INTENT):**

   ```text
   if OWNER_INTENT is present (EVOLUTION_HANDOFF and/or EXPLORE_HANDOFF):
       owner-contract semantic meaning MUST derive primarily from OWNER_INTENT
   else:
       current behavior — Owner request + available change context
   ```

   KEEP/HARD/FORWARD/CURRENT_INCREMENT/IN_SCOPE/OUT_OF_SCOPE and explore
   REPOSITORY_FINDINGS/RUNTIME_MAPPING/evidence MAY refine constraints and
   «Чего не делаем» — they MUST NOT silently redefine what OWNER_INTENT says
   the change is about.

   Use plain human language. Do not use internal orchestration vocabulary
   (evolution links, STAR/INCREMENT ids, HARD/FORWARD, ADL, placement jargon,
   paired regression, authoritative path, etc.) unless those terms are
   themselves part of the Owner's stated task / `OWNER_INTENT`. Do not
   mechanically shorten or copy `proposal.md`. Aim for roughly 10–30
   substantive lines.

   **UI labels preference:** When describing product behavior in Owner Contract,
   prefer the exact button / menu / screen labels the user sees in the UI
   (quote them or write «как на кнопке: …») whenever those labels are known
   from `OWNER_INTENT`, the Owner request, change context, or existing UI
   copy. If no UI label is known, fall back to ordinary domain language —
   never invent button names. This is a preference for the companion
   `owner-contract.md` only, not a scaffold blocker and not a requirement
   for schema artifacts.

   Required structure:

   ```markdown
   # Owner Contract

   ## Что хотим получить

   Короткое описание конечного результата человеческим языком.

   ## Зачем

   Почему изменение вообще нужно и какую проблему решает.

   ## Что должно остаться неизменным

   Только существенные invariants / существующее поведение, которое нельзя случайно сломать.

   ## Чего сейчас не делаем

   Короткий scope-out. Только реально важные границы.

   ## Как поймём, что получилось

   Несколько observable критериев результата человеческим языком.

   ## Решения Owner

   Только существенные semantic/product decisions, которые Owner уже явно принял.

   Если таких решений нет:

   `Нет отдельных решений Owner.`
   ```

   Empty/inapplicable sections may stay minimal. Reflect the original Owner
   request / `OWNER_INTENT` only — no speculative future scope, no invented
   product decisions, and no silent swap to an explore technical framing.

5. **Show the artifact status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Use the returned `planningHome`, `changeRoot`, `artifactPaths`, and `nextSteps` instead of assuming repo-local paths.
   Owner Contract must **not** appear as a schema artifact in this status.

6. **Get instructions for the first artifact**
   The first artifact depends on the schema. Check the status output to find the first artifact with status "ready".
   ```bash
   openspec instructions <first-artifact-id> --change "<name>"
   ```
   This outputs the template and context for creating the first artifact.

7. **STOP and wait for user direction**

**CREATE Output**

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Current status (0/N schema artifacts complete)
- Path to `owner-contract.md` and its full contents (or a short readable rendering) so Owner can verify understanding in tens of seconds
- The template for the first schema artifact
- Soft next: `/opsx-owner-contract-review change=<name>`
- Prompt: "Ready to create the first artifact? Run `/opsx:continue` or just describe what this change is about and I'll draft it."

**CREATE Guardrails**
- Do NOT create schema artifacts yet (proposal/specs/design/decisions/tasks) — only the companion `owner-contract.md` plus scaffold
- Do NOT register Owner Contract in `schema.yaml` or make `continue`/`ff`/`apply`/`verify` require it
- Do NOT inject Owner Contract content into `spec` or other schema artifacts
- Do NOT let explore findings / KEEP/HARD/FORWARD / repository mapping silently
  replace `OWNER_INTENT` as the semantic source of `owner-contract.md`
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists (and no REPAIR handoff), suggest using `/opsx-continue` instead — do not silently REPAIR
- Pass --schema if using a non-default workflow
- Do NOT enter REPAIR MODE without literal `OWNER_REVIEW_HANDOFF` /
  `MODE: REPAIR_EXISTING_OWNER_CONTRACT`
- CREATE does not require `OWNER_REVIEW_HANDOFF`
