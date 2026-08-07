---
component_id: opsx.commands.meta_update_index
component_version: 0.2.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Incremental catalog index from snapshot watermarks; Owner GO; STRUCTURE_HASH path-set integrity"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-INDEX-01
newline_normalization: none
---

# /opsx-meta-update-index

Incremental catalog index over central branch snapshots.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-INDEX-01
WRITES: catalog Git only
```

Tool: `node .opsx/tools/opsx-central-catalog.mjs index-plan|index-apply`  
Schema: `.opsx/shared/command-discovery.md`

## Behavior

1. For each registered snapshot: compare HEAD to `last_indexed_commit`.
2. Equal → `UNCHANGED` (no tree reads). Still report stored `structure_hash`
   when present.
3. Changed → `git diff` / full reindex for that source if watermark missing/non-ancestor.
4. Update `occurrences.ndjson` and regenerate `by-repo` / `by-command` / `by-hash`.
5. After occurrence update for a source: compute `STRUCTURE_HASH` over the
   sorted indexed command path set (paths only, sha256 integrity fingerprint —
   not path encryption). Persist `structure_hash` on `index-state.yaml`.
6. If previous `structure_hash` differs → emit `STRUCTURE_CHANGED` with
   `added_paths` / `removed_paths` (study cue for layout drift). Orthogonal to
   content signals (`NEW_COMPONENT` / `NEW_VARIANT` / `COMMAND_REMOVED`).
7. Advance watermark only after successful catalog commit.

Never writes snapshot trees or local project process files.

## Modes

| Input | Mode |
|---|---|
| default | READ_ONLY plan |
| exact `GO` | APPLY + catalog commit |

## Output

```text
STATUS: PLAN_READY | INDEX_UPDATED | FAIL_CLOSED
RESULTS:
STRUCTURE_SIGNALS: (optional STRUCTURE_CHANGED rows)
NEXT_ACTION: /opsx-meta-discover | /opsx-meta
ORIENTATION_HINT:
  LANE: META
  NEXT_META: /opsx-meta
  NEXT_ACTION:
```
