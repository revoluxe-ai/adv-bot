---
description: "Shared OPSX human-label display contract: Title (machine-id) for inventory/list/pick-list outputs. Cite-only — not a standalone user command."
---

# OPSX Human Label Display Contract

Shared mandatory **human display** contract for inventory / ledger / pick-list
style outputs in OPSX commands.

This file is **not** a user-facing `/opsx-*` workflow command.
Do **not** invoke it as `/opsx-human-label-display`.
Commands that emit multi-item human lists of named artifacts MUST cite and
follow this contract (or an equivalent stricter local specialization).

Companion contracts:

* `.cursor/commands/opsx-execution-preflight.md` — execution cost / hang risk
* `.cursor/commands/opsx-source-resolution.md` — artifact path resolution

This contract covers **how humans see names**, not git/I/O budgets and not
domain ownership of titles.

## Problem solved

Operators must not memorize machine identities (repo paths, CASE_ID,
FINDING_ID, job names, …) to understand or select items in a list.
Primary label is a short human title; machine id is a secondary hint.

## When this applies

Apply when a command produces any of:

* inventory / registry / ledger tables or bullet lists;
* pick-lists / candidate lists after ambiguous resolution;
* status lines naming one of many similar artifacts;
* pasteable `NEXT_ACTION` that targets a listed artifact by name.

Does **not** apply to:

* pure machine receipts meant only for other commands (unless also shown to humans);
* single opaque tokens with no inventory context (e.g. a lone GO token);
* secret values / raw Secret data (still forbidden elsewhere).

## Display form (mandatory)

```text
Title (machine-id)
```

Examples:

```text
Export non-zero balance users (scripts/export_non_zero_balance_users.py)
Claim next finding (FINDING_ID=abc123)
```

Rules:

1. **Title first** — short human name the Owner can recognize.
2. **Machine id in parentheses** — path, durable id, or equivalent.
3. Path/id alone is **not** the primary human label in inventory/list output.
4. Tools (kubectl, pytest paths, Job templates) still use the resolved
   machine id internally.

## Title ownership

* The **owning command / ledger** defines how titles are stored and assigned
  (e.g. `/opsx-scripts` + `scripts/REGISTRY.md` field `title`).
* This contract does not create a second title SoT.
* Prefer stable titles; Owner may rename in the owning ledger.

## Selection tokens (when the command exposes them)

If a command accepts a selector such as `script=`, `case=`, `finding=`:

1. Accept human **title** and/or **machine id** as documented locally.
2. Resolve: exact machine-id match → else case-insensitive exact title →
   else unique case-insensitive title substring (only if local command allows).
3. Ambiguous or none → `STATUS=BLOCKED` (or command-equivalent) and list
   candidates as `Title (machine-id)`.
4. Pasteable next actions may use the title when unique; still show
   `Title (machine-id)` once in `WHAT_HAPPENED` / plan body.

## Local specialization

A command MAY add stricter rules (required ledger `title` column, docstring
derivation, …) but MUST NOT weaken this form for human inventory/list lines.

Reference specialization: `.cursor/commands/opsx-scripts.md`
(scripts `title` + `Title (path)`).

## Non-goals

* Not a runnable command or pipeline hard gate.
* Not a substitute for `/opsx-verify`, archive, or product GO.
* Not authorization to invent titles outside the owning ledger’s rules.
* Not a license to dump entire command-sets while “checking labels”.

## Self-check (for citing commands)

- [ ] Human inventory/list lines use `Title (machine-id)`
- [ ] Ambiguous title/id resolution lists candidates in the same form
- [ ] Machine id remains available for tools
- [ ] No second authoritative title registry invented here
