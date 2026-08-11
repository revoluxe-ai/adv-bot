---
name: /opsx-new
id: opsx-new
category: Workflow
description: Start a new change (CREATE) or repair existing owner-contract.md from OWNER_REVIEW_HANDOFF (REPAIR)
---

Start a new change using the experimental artifact-driven approach, **or**
repair an existing Change's `owner-contract.md` from a valid
`OWNER_REVIEW_HANDOFF`.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md` when exact paths/IDs appear later in the workflow; this command must not inventory unrelated trees first.

## Authority

```text
Owner                      → product semantics / unresolved decisions
opsx-owner-contract-review → READ_ONLY diagnosis + OWNER_REVIEW_HANDOFF
opsx-new                   → sole writer of owner-contract.md
                             (CREATE or REPAIR_EXISTING_OWNER_CONTRACT)
```

No other command gains write authority over `owner-contract.md` from this
loop. This command never edits proposal/spec/design/tasks/decisions/code
in REPAIR MODE.

## Mode dispatch (mandatory — first)

Before CREATE scaffolding, inspect the user input for an explicit repair
trigger. Do **not** guess from natural language (“похоже хочет поправить”).

```text
IF input contains literal block:
     OWNER_REVIEW_HANDOFF
     ...
     MODE: REPAIR_EXISTING_OWNER_CONTRACT
  → enter REPAIR MODE (below)

ELSE
  → enter CREATE MODE (legacy behavior)
```

| Mode | Condition | Writes |
|------|-----------|--------|
| `CREATE` | No valid REPAIR handoff; new change name/description | scaffold + new `owner-contract.md` only |
| `REPAIR` | Valid `OWNER_REVIEW_HANDOFF` with `MODE: REPAIR_EXISTING_OWNER_CONTRACT` + existing change + existing `owner-contract.md` | **only** that `owner-contract.md` |

If a change with the given name already exists **and** there is **no** valid
REPAIR handoff → suggest `/opsx:continue` (do **not** silently enter REPAIR;
do **not** recreate scaffold).

---

# REPAIR MODE

## Trigger (formal)

Required literal markers in input (same contract as
`/opsx-owner-contract-review` READY_FOR_REPAIR output):

```text
OWNER_REVIEW_HANDOFF
CHANGE_ID: <change>
TARGET_WRITER: /opsx-new
MODE: REPAIR_EXISTING_OWNER_CONTRACT
```

Plus non-empty `REPAIRS_REQUIRED`, `WRITE_BOUNDARY` permitting
`owner-contract.md` only, and `DO_NOT_CHANGE` / `FORBIDDEN` as emitted by
the reviewer.

## Input validation (before any write)

Validate **all** of the following. On any failure → **PAUSE** (no writes)
with the exact missing/invalid field — never best-effort rewrite.

```text
1. CHANGE_ID present and resolvable under openspec/changes/<CHANGE_ID>/
2. owner-contract.md exists at that change root
3. TARGET_WRITER == /opsx-new
4. MODE == REPAIR_EXISTING_OWNER_CONTRACT
5. REPAIRS_REQUIRED is non-empty
6. every R-* has REQUIRED_SEMANTICS that is fully resolved
   (no A/B choice for the writer; no OWNER_INPUT_REQUIRED: YES)
7. WRITE_BOUNDARY permits owner-contract.md only
8. FORBIDDEN / WRITE_BOUNDARY do not request edits to
   proposal/spec/design/tasks/decisions/evolution/explore/code/tests
```

Failure tokens:

| Condition | Status |
|-----------|--------|
| Missing/invalid required field | `PAUSE` / `INVALID_REPAIR_HANDOFF` + field name |
| Repair asks writer to choose A/B or unresolved semantics | `PAUSE` / `UNRESOLVED_SEMANTIC_CHOICE` — must **not** choose |
| WRITE_BOUNDARY / repair targets non-owner-contract artifact | `PAUSE` / `INVALID_REPAIR_BOUNDARY` + path |
| Change or owner-contract.md missing | `PAUSE` / `MISSING_TARGET` |

## Write boundary

Allowed write path (exactly one):

```text
openspec/changes/<CHANGE_ID>/owner-contract.md
```

**Must not** create/modify:

```text
proposal.md, design.md, tasks.md, specs/**, decisions/**
evolution / explore artifacts, main specs, archive, code, tests
```

If a listed repair requires another artifact → `PAUSE` /
`DEPENDENCY_FOUND` — do **not** expand write scope.

## Repair semantics (constrained patch)

Treat `OWNER_REVIEW_HANDOFF` as a constrained patch contract.

MAY:

* rephrase a section to match `REQUIRED_SEMANTICS`
* remove a stale assumption named by an R-*
* add a confirmed Owner decision from `CONFIRMED_OWNER_DECISIONS` / R-*
* align acceptance wording to confirmed semantics
* resolve an internal contradiction **only** as `REQUIRED_SEMANTICS` states

MUST NOT:

* propose a new product rule
* choose an unresolved A/B
* change neighboring semantics “for polish”
* rewrite the whole contract from scratch unless every section is in
  `REPAIRS_REQUIRED`
* alter `DO_NOT_CHANGE` semantics
* reinterpret `OWNER_INTENT`
* create schema artifacts

## Apply procedure

1. Read current `owner-contract.md`.
2. Apply each `R-*` in order to match `REQUIRED_SEMANTICS`.
3. Preserve every `DO_NOT_CHANGE` item.
4. Merge `CONFIRMED_OWNER_DECISIONS` into `## Решения Owner` only where an
   R-* or explicit repair requires it (do not invent extras).
5. **Atomicity:** if any required R-* cannot be applied safely → do **not**
   claim success. Prefer `PAUSE` / `REPAIR_NOT_COMPLETE` naming the exact
   `R-*`. Do not silently ship a partial semantic repair as success.
6. If a write occurs, the resulting file must satisfy all R-* **or** the
   result must explicitly report incomplete (never green-wash).

## Preservation check (local writer — not a substitute for review)

Before finishing a successful repair, verify:

```text
1. every R-* reflected in owner-contract.md
2. every DO_NOT_CHANGE preserved
3. no new product semantics introduced beyond handoff
4. CONFIRMED_OWNER_DECISIONS not distorted
5. write boundary not violated (OTHER_FILES_CHANGED: none)
```

## Idempotency

Re-running the **same** valid handoff after a successful repair:

* must not create duplicate bullets/sections
* must not broaden edits beyond `REPAIRS_REQUIRED`
* resulting contract remains semantically equivalent
* report `already satisfied` for R-* items that already match
  `REQUIRED_SEMANTICS`

## REPAIR MODE output

```text
OWNER_CONTRACT_REPAIR_RESULT
CHANGE_ID: <change>
MODE: REPAIR_EXISTING_OWNER_CONTRACT

REPAIRS_APPLIED:
- R-001
- R-002
...

REPAIRS_NOT_APPLIED:
- none | <R-* + reason>

FILES_CHANGED:
- openspec/changes/<change>/owner-contract.md

OTHER_FILES_CHANGED:
none

NEW_PRODUCT_DECISIONS_INTRODUCED:
none

NEXT_ACTION:
/opsx-owner-contract-review change=<change>
```

Then show the resulting `owner-contract.md` (full or sufficiently complete
for Owner skim). Final semantic `PASS` belongs **only** to independent
`/opsx-owner-contract-review` — never emit review `PASS` from this command.

STOP after repair output. Do not create proposal/spec/design/tasks.

Regression fixtures: `.cursor/commands/_fixtures/opsx-new-owner-contract-repair/`

---

# CREATE MODE

**Input**: The argument after `/opsx:new` is the change name (kebab-case), OR a description of what the user wants to build. (No REPAIR handoff present.)

**Steps**

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
   suggest `/opsx:continue` instead. Do not recreate scaffold.

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

**CREATE Output**

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Current status (0/N schema artifacts complete)
- Path to `owner-contract.md` and its full contents (or a short readable rendering) so Owner can verify understanding in tens of seconds
- The template for the first schema artifact
- Prompt: "Ready to create the first artifact? Run `/opsx:continue` or just describe what this change is about and I'll draft it."
  Soft recommendation (not a hard gate): run
  `/opsx-owner-contract-review change=<name>` before continue/ff.

**CREATE Guardrails**
- Do NOT create schema artifacts yet (proposal/specs/design/decisions/tasks) — only the companion `owner-contract.md` plus scaffold
- Do NOT register Owner Contract in `schema.yaml` or make `continue`/`ff`/`apply`/`verify` require it
- Do NOT inject Owner Contract content into `spec` or other schema artifacts
- Do NOT let explore findings / KEEP/HARD/FORWARD / repository mapping silently
  replace `OWNER_INTENT` as the semantic source of `owner-contract.md`
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists and no REPAIR handoff is present, suggest using `/opsx:continue` instead
- Pass --schema if using a non-default workflow
- Do NOT enter REPAIR MODE from vague natural language without the literal
  `OWNER_REVIEW_HANDOFF` / `MODE: REPAIR_EXISTING_OWNER_CONTRACT` trigger
