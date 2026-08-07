---
component_id: opsx.commands.projectize
component_version: 0.4.0
runtime_class: ACTIVE
ownership: TARGET_ONLY
contract_id: OPSX-GAME-FULL-BODY-CORRECTION-01
canonical_source_body: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

Target-only generated command. No canonical source body.

# /opsx-projectize

Projectization of imported **or bootstrap-seeded** OPSX/OpenSpec surfaces for
this Vue/npm game repository.

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
   `.tmp/opsx-bootstrap/*/MERGE_RECEIPT.md` when present in this chat.
2. Classify each: `KEEP` / `DELETE` / `REWRITE` / `DEFER`.
3. Enumerate destructive paths (source changes/archives/specs/decisions/config).
4. Detect target capabilities via `.opsx/adapters/vue-npm/` + `package.json` scripts.
5. Show activation changes and unresolved items.
6. **No writes.**

### `/opsx-projectize:GO` (authorized apply)

Requires explicit Owner GO (this task contract `OPSX-GAME-EXECUTION-01` grants the first run).

Apply the plan:

1. Remove source changes / archives / product specs if present.
2. Reset decisions registry to clean template+index.
3. Regenerate `openspec/config.yaml` from target facts.
4. Adapt policies, schemas/templates, commands/rules/pipeline.
5. Update activation + provenance.
6. Write `.opsx/project/manual_review.md`.
7. Set `.opsx/projectization.yaml` to `COMPLETE` only after checks pass.

## Lock semantics

While `.opsx/projectization.yaml` has `status: REQUIRED`, mutation commands fail closed:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

After `COMPLETE`, a second `:GO` without Owner reset must fail closed.

## Forbidden

- Modifying `src/**`, `public/**`, `package.json`, lockfile, vue config.
- Installing dependencies.
- Commit / push / PR / deploy.
- Importing WB product state into the active tree.

## When not to use (after COMPLETE)

After `.opsx/projectization.yaml` is `COMPLETE`, do **not** use this command
to ingest a newer OPSX archive or peer repo. Prefer:

- profile / central rebind → `/opsx-meta-bootstrap`
- one command from catalog/donor → `/opsx-meta-import-command`

A second `/opsx-projectize:GO` without Owner reset remains fail-closed.
