---
component_id: opsx.commands.projectize
component_version: 0.5.0
runtime_class: ACTIVE
ownership: TARGET_ONLY
contract_id: OPSX-WB-PROJECTIZE-01
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "v0.5 WB/poetry projectize: never wipe product openspec; vue-npm not assumed; Owner GO 2026-08-07"
---

# TARGET OVERRIDE — HIGHEST PRIORITY

Target-only generated command. No canonical source body.

# /opsx-projectize

Projectization of imported **or bootstrap-seeded** OPSX/OpenSpec surfaces for
this **WB Sky / Poetry (Python)** repository (`adv-bot` family).

## Runtime class

`ACTIVE`

## Upstream of surfaces

Typical producers of the tree this command adapts:

- `/opsx-meta-bootstrap` — first-contact `BOOTSTRAP_PROFILE` seed/bind (may leave
  `projectization.yaml` at `REQUIRED`)
- `/opsx-meta-import-command` — command-centric merges after COMPLETE (not a
  substitute for first projectize)
- Historical zip / manual allowlisted copy

If `.opsx/` is absent entirely, do **not** invent a skeleton here — hand off:

```text
NEXT_COMMAND: /opsx-meta-bootstrap
```

## Modes

### `/opsx-projectize` (read-only)

1. Inventory imported/raw/**bootstrap-staged** surfaces (commands, rules,
   pipeline, openspec, `.opsx`). Prefer citing
   `.opsx/runs/bootstrap/*/MERGE_RECEIPT.md` when present in this chat.
2. Classify each: `KEEP` / `DELETE` / `REWRITE` / `DEFER`.
3. Enumerate destructive paths — and mark which are **forbidden** on this
   product tree (existing WB `openspec/**` must stay).
4. Detect target capabilities via `pyproject.toml` / Poetry, `app/`, tests,
   and `.opsx/adapters/poetry-python/` (not Vue/`package.json` game scripts).
5. Show activation changes and unresolved items.
6. **No writes.**

### `/opsx-projectize:GO` (authorized apply)

Requires explicit Owner `:GO`.

Apply a **product-safe** plan for this repo:

1. **Do not** remove `openspec/changes/**`, `openspec/changes/archive/**`,
   `openspec/specs/**`, or accepted `openspec/decisions/**`.
2. **Do not** reset the decisions registry to empty when product decisions exist.
3. **Do not** regenerate `openspec/config.yaml` from a foreign game template;
   keep WB Sky product config unless Owner explicitly authorizes a rewrite.
4. Rewrite game-/vue-tainted process commands and adapter refs for Poetry/WB.
5. Update `.opsx/manifest.yaml`, adapters, activation + provenance.
6. Write `.opsx/project/manual_review.md`.
7. Set `.opsx/projectization.yaml` to `COMPLETE` only after checks pass
   (openspec product tree intact; required gate commands present; lock coherent).

## Lock semantics

While `.opsx/projectization.yaml` has `status: REQUIRED`, mutation commands fail closed:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

After `COMPLETE`, a second `:GO` without Owner reset must fail closed.

## Forbidden

- Modifying `app/**` product code, `tests/**` (except process-only if Owner asks),
  `pyproject.toml`, Poetry lock, `.env*`.
- Installing dependencies.
- Commit / push / PR / deploy.
- Assuming or seeding `.opsx/adapters/vue-npm/**`.
- Blind wipe of product OpenSpec state from a game donor plan.

## When not to use (after COMPLETE)

After `.opsx/projectization.yaml` is `COMPLETE`, do **not** use this command
to ingest a newer OPSX archive or peer repo. Prefer:

- profile / central rebind → `/opsx-meta-bootstrap`
- one command from catalog/donor → `/opsx-meta-import-command`

A second `/opsx-projectize:GO` without Owner reset remains fail-closed.
