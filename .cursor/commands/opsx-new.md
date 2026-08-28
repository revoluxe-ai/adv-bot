---
component_id: opsx.commands.new
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: adapted_target_native
required_adapters: ["opsx-lite", "poetry-python"]
local_modification_note: "Inbound KEEP opsx-new UPDATED_COMMAND from catalog OCCURRENCE=ba52fae55cd2632e (adv-bot/split-payment); CREATE+REPAIR owner-contract modes; WB/poetry-python target-native; game/vue-npm fork skipped"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-NEW-01
newline_normalization: none
donor_source_id: adv-bot/split-payment-for-adv-without-pay-for-adv-on-pauses
donor_snapshot_head: db91149ae1d96d1fd85ceae7a405e65c09f0c29b
donor_occurrence_id: ba52fae55cd2632e
donor_full_file_hash: e265586f3064ca000168f5e7762eb8b080a810894d40a363ae7c0fbe4a9d048b
inbound_packet: .tmp/opsx-inbound/20260816T154000Z/DIFF_PACKET.md
name: /opsx-new
id: opsx-new
category: Workflow
description: Start a new change (CREATE) or repair existing owner-contract.md from OWNER_REVIEW_HANDOFF (REPAIR)
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-NEW-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority paths

- Changes (write in REPAIR): `openspec/changes/<CHANGE_ID>/owner-contract.md` only
- Changes (write in CREATE): `<changeRoot>/owner-contract.md` after scaffold
- Review handoff (read): `/opsx-owner-contract-review` `OWNER_REVIEW_HANDOFF`
- Adapter (read): `.opsx/adapters/poetry-python/README.md`
- Fixtures (read): `.cursor/commands/_fixtures/opsx-new-owner-contract-repair/**`

### Hard target bans

- Do not install dependencies / modify `package.json`, Poetry lock, or `pyproject.toml`.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not activate game/Vue/`vue-npm` / `npm run build` assumptions from donor forks.
- REPAIR: do not write proposal, design, specs, tasks, decisions, or product code.
- CREATE: do not register `owner-contract.md` in schema or advance beyond first-artifact template without Owner direction.
- Never emit independent `/opsx-owner-contract-review` PASS from `/opsx-new`.

### Projectization gate

Read `.opsx/projectization.yaml` before any run.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

---
# /opsx-new

Start a new change using the experimental artifact-driven approach, **or**
repair an existing Change's `owner-contract.md` from a valid
`OWNER_REVIEW_HANDOFF`.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: The argument after `/opsx:new` is the change name (kebab-case), OR a description of what the user wants to build, **or** a pasteable `/opsx-new` + `OWNER_REVIEW_HANDOFF` block from `/opsx-owner-contract-review`.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md` when exact paths/IDs appear later in the workflow; this command creates a new change and should not inventory unrelated trees first.

**Regression fixtures (dry-run / acceptance):**
`.cursor/commands/_fixtures/opsx-new-owner-contract-repair/`

## Mode detection (mandatory first)

Before any CREATE scaffolding:

```text
if input contains literal OWNER_REVIEW_HANDOFF
   AND MODE: REPAIR_EXISTING_OWNER_CONTRACT:
    → enter REPAIR MODE (do not run CREATE steps)
else:
    → CREATE MODE (legacy path below)
```

Do **not** enter REPAIR MODE from vague natural language (“fix the contract”,
“repair owner contract”, “update companion”) without that literal handoff
trigger. `TARGET_WRITER: /opsx-new` when present must match; reject handoffs
aimed at another writer.

Accept the reviewer pasteable block **without** field renaming. Forbidden
aliases (do not require Owner to adapt): `REVIEW_SOURCE`, `REPAIR_BOUNDARY`,
`REPAIR_COMMAND`, `CURRENT_TEXT`.

---

## REPAIR MODE

Sole writer path for bounded repairs to an **existing** `owner-contract.md`
from `/opsx-owner-contract-review` `READY_FOR_REPAIR`.

### REPAIR Steps

1. **Parse handoff**
   Require literal fields (shared contract with OCR):
   `CHANGE_ID`, `MODE: REPAIR_EXISTING_OWNER_CONTRACT`,
   `REVIEWED_ARTIFACT`, `OWNER_INTENT`, `CONFIRMED_OWNER_DECISIONS`,
   `REPAIRS_REQUIRED`, `DO_NOT_CHANGE`, `WRITE_BOUNDARY`, `FORBIDDEN`,
   `AFTER_REPAIR`. Resolve target path from `CHANGE_ID` /
   `REVIEWED_ARTIFACT` → existing
   `openspec/changes/<CHANGE_ID>/owner-contract.md` (or store-resolved
   equivalent). Change + file **must already exist**.

2. **Validate before any write** — on failure `PAUSE`, `FILES_CHANGED: none`:
   - Missing/invalid shell, wrong `TARGET_WRITER`, missing change or
     `owner-contract.md` → `INVALID_REPAIR_HANDOFF`
   - Any `R-*` with unresolved A/B choice, `OWNER_INPUT_REQUIRED: YES`,
     or incomplete `REQUIRED_SEMANTICS` → `UNRESOLVED_SEMANTIC_CHOICE`
     (or `INVALID_REPAIR_HANDOFF` naming the `R-*`); do **not** pick A/B
   - `WRITE_BOUNDARY` not limited to `owner-contract.md` only, **or**
     repairs/FORBIDDEN imply edits to proposal/spec/design/tasks/
     decisions/code/tests/Evolution/Explore → `INVALID_REPAIR_BOUNDARY`
     (do **not** partially edit the contract and claim success)

3. **Hard non-actions while repairing**
   - Do **not** run `openspec new change`
   - Do **not** recreate scaffold
   - Do **not** create or edit proposal/spec/design/decisions/tasks
   - Do **not** reinterpret `OWNER_INTENT` or invent new product decisions
   - Do **not** emit independent OCR `PASS` from `/opsx-new`

4. **Apply bounded repairs**
   Edit **only** `owner-contract.md`. For each `R-*` in
   `REPAIRS_REQUIRED`, rewrite the named section so
   `REQUIRED_SEMANTICS` is true (evidence-backed). Preserve every
   `DO_NOT_CHANGE` item. Do not polish unrelated sections. Fold
   `CONFIRMED_OWNER_DECISIONS` into «Решения Owner» only as stated —
   no extras.

5. **Idempotency**
   If a re-pasted identical handoff finds `REQUIRED_SEMANTICS` already
   satisfied: do not duplicate bullets/sections; do not broaden edits.
   List those `R-*` as already satisfied under `REPAIRS_APPLIED` (or note
   under `REPAIRS_NOT_APPLIED` with already-satisfied) and keep
   `OTHER_FILES_CHANGED: none`.

6. **STOP after repair result**
   Do not advance into CREATE status/instructions / first-artifact drafting.

### REPAIR Output

Emit:

```text
MODE: REPAIR_EXISTING_OWNER_CONTRACT
CHANGE_ID: <change>
FILES_CHANGED:
  openspec/changes/<CHANGE_ID>/owner-contract.md
OTHER_FILES_CHANGED: none

OWNER_CONTRACT_REPAIR_RESULT
REPAIRS_APPLIED:
  - R-*: <short note>
REPAIRS_NOT_APPLIED: none | <list with reason>
NEW_PRODUCT_DECISIONS_INTRODUCED: none
NEXT_ACTION: /opsx-owner-contract-review change=<CHANGE_ID>
```

On validation pause:

```text
MODE: REPAIR_EXISTING_OWNER_CONTRACT
PAUSE
REASON: UNRESOLVED_SEMANTIC_CHOICE | INVALID_REPAIR_BOUNDARY | INVALID_REPAIR_HANDOFF
FILES_CHANGED: none
```

### REPAIR Guardrails

- Write boundary: `owner-contract.md` only
- Do NOT scaffold, recreate, or touch schema artifacts
- Do NOT enter REPAIR from vague NL without literal handoff + mode
- Do NOT require Owner to rewrite OCR field names
- Do NOT claim review PASS; next hop is `/opsx-owner-contract-review`
- Acceptance dry-run: fixtures `01`–`07` under
  `_fixtures/opsx-new-owner-contract-repair/`

---

## CREATE MODE

Use only when Mode detection did **not** select REPAIR.

### CREATE Steps

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
   suggest `/opsx:continue` instead. Do not recreate scaffold. Do **not**
   silently enter REPAIR.

4. **Create Owner Contract (companion file — not a schema artifact)**

   Immediately after a successful scaffold, write
   `<changeRoot>/owner-contract.md` from the Owner request and available
   change context.

   This file is a **human-facing companion** for Owner review. It is **not**
   registered in the OpenSpec schema, **not** part of `openspec status`
   artifact sequence, and **must not** be copied into `spec` or treated as
   canonical authority for specs/design/tasks.

   **Semantic source priority (OWNER_INTENT):**

   Standard flow input may include `EVOLUTION_HANDOFF` and/or
   `EXPLORE_HANDOFF`.

   ```text
   if OWNER_INTENT is present:
       owner-contract semantic meaning ("Что хотим получить", observable
       "Как поймём…", and Owner product meaning in "Решения Owner")
       MUST derive primarily from OWNER_INTENT
   else:
       current behavior — Owner request + available change context
   ```

   When `OWNER_INTENT` is present, treat other inputs as
   constraints/context only — not as a replacement task object:

   - `KEEP` / `HARD` / `FORWARD_COMPATIBILITY` / `CURRENT_INCREMENT`
   - `IN_SCOPE` / `OUT_OF_SCOPE`
   - explore `REPOSITORY_FINDINGS` / `RUNTIME_MAPPING` / evidence
   - agent inference

   Those fields MAY refine «Что должно остаться неизменным», «Чего сейчас
   не делаем», and constraints — they MUST NOT silently redefine what
   `OWNER_INTENT` says the change is about. Do not synthesize a new Owner
   meaning by blending all handoff fields equally.

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

### CREATE Output

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Current status (0/N artifacts complete)
- The template for the first artifact
- Soft next: `/opsx-owner-contract-review change=<name>` (recommended before continue/ff)
- Prompt: "Ready to create the first artifact? Run `/opsx:continue` or just describe what this change is about and I'll draft it."

### CREATE Guardrails

- Do NOT create schema artifacts yet (proposal/specs/design/decisions/tasks) — only the companion `owner-contract.md` plus scaffold
- Do NOT register Owner Contract in `schema.yaml` or make `continue`/`ff`/`apply`/`verify` require it
- Do NOT inject Owner Contract content into `spec` or other schema artifacts
- Do NOT let explore findings / KEEP/HARD/FORWARD / repository mapping silently
  replace `OWNER_INTENT` as the semantic source of `owner-contract.md`
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists (and no REPAIR handoff), suggest using `/opsx:continue` instead — do not silently REPAIR
- Pass --schema if using a non-default workflow
- Do NOT enter REPAIR MODE from vague natural language without the literal
  `OWNER_REVIEW_HANDOFF` / `MODE: REPAIR_EXISTING_OWNER_CONTRACT` trigger
- CREATE does not require `OWNER_REVIEW_HANDOFF`