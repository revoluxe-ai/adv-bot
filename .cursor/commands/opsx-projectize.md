---
component_id: opsx.commands.projectize
component_version: 0.5.0
runtime_class: ACTIVE
ownership: TARGET_ONLY
contract_id: OPSX-SCRIPTS-PROJECTIZE-01
canonical_source_body: none
required_adapters: ["opsx-lite", "poetry-scripts"]
local_modification_note: "2026-08-07 projectize:GO — retarget WB Sky / scripts (Poetry); no Vue wipe"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
---

# TARGET OVERRIDE — HIGHEST PRIORITY

Target-only command for **meta-repo/scripts** (WB Sky, Poetry/Python).
No canonical upstream body. Stack-agnostic bans retained.

# /opsx-projectize

Projectization of imported **or bootstrap-seeded** OPSX surfaces for this
**scripts** consumer (`repo_family_id: scripts`).

## Runtime class

`ACTIVE`

## Upstream of surfaces

Typical producers:

- `/opsx-meta-bootstrap` — first-contact seed/bind (may leave `REQUIRED`)
- `/opsx-meta-import-command` — extras after COMPLETE
- Historical allowlisted copy

If `.opsx/` is absent entirely:

```text
NEXT_COMMAND: /opsx-meta-bootstrap
```

## Modes

### `/opsx-projectize` (read-only)

1. Inventory commands, rules, pipeline, openspec, `.opsx`. Cite
   `.tmp/opsx-bootstrap/*/MERGE_RECEIPT.md` when present.
2. Classify: `KEEP` / `DELETE` / `REWRITE` / `DEFER`.
3. Enumerate destructive paths — for scripts, **product** `openspec/**` and
   `app/**` default to **KEEP** (not foreign game dumps).
4. Detect capabilities via `.opsx/adapters/poetry-scripts/` + `pyproject.toml`
   / Poetry scripts (not `vue-npm` / Vue `package.json`).
5. Show activation changes and unresolved items.
6. **No writes.**

### `/opsx-projectize:GO` (authorized apply)

Requires explicit Owner `:GO`.

**Scripts-native apply (default):**

1. REWRITE game-shaped hub/projectize text for Poetry/scripts.
2. Seed/refresh `.opsx/adapters/poetry-scripts/` (no dependency installs).
3. Update activation + provenance registries.
4. Rewrite `.opsx/project/manual_review.md` for this target.
5. Update `.opsx/manifest.yaml` / `.opsx/lock.yaml` stubs for `scripts`.
6. Set `.opsx/projectization.yaml` to `COMPLETE` only after checks pass.

**Default KEEP (do not destroy):**

- `openspec/changes/**`, `openspec/decisions/**`, `openspec/specs/**`
- `openspec/config.yaml` (WB Sky product config)
- `app/**`, Poetry lockfiles, `.env*`

**Only with Owner-explicit wipe tokens** may product OpenSpec trees be reset
(not part of bare `:GO`).

## Lock semantics

While `status: REQUIRED`, mutation commands fail closed:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

After `COMPLETE`, a second `:GO` without Owner reset must fail closed.

## Forbidden

- Modifying `app/**`, `src/**`, `public/**`, `package.json`, `poetry.lock`,
  Vue config (N/A), `.env*`.
- Installing dependencies (`poetry install` / npm).
- Commit / push / PR / deploy.
- Blind wipe of product OpenSpec on bare `:GO`.
- Importing foreign product dumps into the active tree.

## When not to use (after COMPLETE)

- Profile / central rebind → `/opsx-meta-bootstrap`
- One extra command → `/opsx-meta-import-command`

A second `/opsx-projectize:GO` without Owner reset remains fail-closed.
