---
component_id: opsx.commands.meta_sync_models
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Materialized Cursor model registry; SHOW without network; UPDATE live sync"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-SYNC-MODELS-01
newline_normalization: none
---

# /opsx-meta-sync-models

SHOW materialized Cursor model catalog or UPDATE from live API.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-SYNC-MODELS-01
WRITES: .cursor/pipeline/shared/MODEL_REGISTRY.json (UPDATE GO only)
```

## Purpose

Single owner for **materialized** model slug list used by orchestrator commands
(`/opsx-supervisor`, `/opsx-bug-team`, `/opsx-commit-all`, …) for exact
`MODEL=<slug>` validation — no silent Fast / mini substitution.

## Human workflow

| Invocation | Network | Writes | Effect |
|---|---|---|---|
| `/opsx-meta-sync-models` | **no** | no | Print registry from disk |
| `/opsx-meta-sync-models UPDATE` | yes | no | Live fetch + table + diff plan |
| `/opsx-meta-sync-models UPDATE GO` | yes | yes | Fetch + materialize JSON + table |

**Default (no tokens):** read-only SHOW — **never** calls Cursor API.

**UPDATE:** refresh from `GET https://api.cursor.com/v1/models` (httpx helper),
show table, report added/removed/changed slugs.

**UPDATE GO:** same as UPDATE + write materialized snapshot.

## When to use

- Before choosing `MODEL=composer-2.5` vs `composer-2.5-fast` in orchestrators
- After Cursor upgrade or plan change
- When `BLOCKED_INVALID_MODEL` and you need authoritative slugs

## When not to use

- Product implementation, commits, bug fixes
- Central command catalog discovery → `/opsx-meta-discover`
- Patch orchestrator contracts → `/opsx-meta-fix-command-defects`

## Artifacts

```text
REGISTRY:  .cursor/pipeline/shared/MODEL_REGISTRY.json
META:      .cursor/pipeline/shared/MODEL_REGISTRY.meta.json
SCHEMA:    .cursor/pipeline/shared/MODEL_REGISTRY.schema.json
TOOL:      .cursor/tools/sync-cursor-models.py
```

Registry always includes **pseudo_models**:

```text
inherit — parent chat agent model (explicit Task inherit)
auto    — explicit platform Auto (not silent omit)
```

Live API models are stored with `slug`, `display_name`, `variant_group`,
`is_fast_variant`, optional `parameters` / `preset_variants`.

## Execution

Follow `.cursor/commands/opsx-execution-preflight.md` (bounded Read).

1. Projectization gate (`.opsx/projectization.yaml` `status: COMPLETE`).
2. Parse tokens:
   - `UPDATE` present → update path
   - exact `GO` + `UPDATE` → write authorized
   - else → SHOW path
3. Run helper from repo root:

```text
# SHOW (default) — no API
poetry run python .cursor/tools/sync-cursor-models.py show

# UPDATE plan (live fetch, no write)
poetry run python .cursor/tools/sync-cursor-models.py update

# UPDATE GO (live fetch + materialize)
poetry run python .cursor/tools/sync-cursor-models.py update --write
```

If `poetry run` unavailable, `python .cursor/tools/sync-cursor-models.py …`
from repo root is acceptable when Python 3.11+ is active.

4. Print helper stdout verbatim; append command envelope below.

### Credentials (UPDATE only)

```text
CURSOR_API_KEY — required for UPDATE / UPDATE GO
```

Never print, log, or commit the key value.

### Capability gaps (FAIL_CLOSED)

| Condition | STATUS |
|---|---|
| No registry on SHOW | `BLOCKED_NO_REGISTRY` |
| No `CURSOR_API_KEY` on UPDATE | `BLOCKED_MISSING_CREDENTIAL` |
| `httpx` missing in Poetry env | `BLOCKED_MISSING_CAPABILITY` |
| API failure | `BLOCKED_API_ERROR` |

Never PASS-by-absence when live fetch was requested.

Uses project `httpx` (no `cursor-sdk` required).

## Downstream contract

Authority: `.cursor/pipeline/shared/MODEL_DISPATCH.md`

Orchestrators MUST:

- pass Task `model: inherit` explicitly (never omit, never silent Auto)
- reject `model: auto` and mini/premium slug fallbacks under interim policy
- `MODEL=<slug>` Owner override — deferred; when enabled, exact registry match
- never upgrade `composer-2.5` → `composer-2.5-fast` silently

Wired by `/opsx-meta-fix-command-defects` (inherit-only packet).

## Hard bans

- No commit / push / PR from this command
- No product code edits
- No secrets in registry files
- SHOW must not perform network I/O
- UPDATE without GO must not write registry files

## Output envelope

Append after helper output:

```text
STATUS: SHOWN | PLAN_READY | SYNCED | BLOCKED_NO_REGISTRY | BLOCKED_MISSING_CREDENTIAL | BLOCKED_MISSING_CAPABILITY | BLOCKED_API_ERROR | FAIL_CLOSED
MODE: READ_ONLY | UPDATE_PLAN | UPDATE_APPLY
REGISTRY_PATH:
SYNCED_AT:
SOURCE:
MODEL_COUNT:
ADDED:
REMOVED:
CHANGED:
WRITE_PERFORMED: yes | no
NEXT_ACTION:
ORIENTATION_HINT:
  LANE: META
  NEXT_META: /opsx-meta
  NEXT_ACTION:
```

### NEXT_ACTION matrix

| STATUS | NEXT_ACTION |
|---|---|
| `SHOWN` | Pick `MODEL=<slug>` for orchestrator commands |
| `PLAN_READY` | `Reply: GO` on same UPDATE invocation → `/opsx-meta-sync-models UPDATE GO` |
| `SYNCED` | `/opsx-meta-fix-command-defects` (wire consumers) then `/opsx-meta-commit` |
| `BLOCKED_NO_REGISTRY` | `/opsx-meta-sync-models UPDATE GO` (needs `CURSOR_API_KEY`) |
| `BLOCKED_MISSING_CREDENTIAL` | Set `CURSOR_API_KEY`, retry UPDATE |
| `BLOCKED_MISSING_CAPABILITY` | `poetry install` (httpx in main deps) |

## Self-review

- Default invocation = disk SHOW only
- UPDATE always shows table after live fetch
- Materialize only on UPDATE GO
- Pseudo models always listed in output
- No commit performed here
