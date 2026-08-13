# OPSX command discovery packet

Shared contract for `/opsx-meta-discover`, design/fix preflight, and
`/opsx-meta-import-command`. Discover owns facts; import owns writes.

## Freshness

```text
INDEX_STATUS: FRESH | STALE | MISSING | UNAVAILABLE
SOURCE_ID:
SNAPSHOT_HEAD:
LAST_INDEXED_COMMIT:
STRUCTURE_HASH:
```

Stale + no candidate ⇒ consumers MUST NOT claim authoritative
`NEW_COMMAND_REQUIRED`, `NOT_FOUND`, or `LOCAL_FIX_REQUIRED` without
`LOCAL_ONLY_CONFIRMED`.

## Structure integrity (per SOURCE_ID)

Catalog index MUST fingerprint the **path set** of indexed commands, not only
file contents. This is a sha256 integrity fingerprint (not path encryption).

```text
STRUCTURE_HASH
```

Computation (index-apply, per source after occurrence update):

1. Collect sorted unique `COMMAND_PATH` values for that `SOURCE_ID`
   (indexed `.cursor/commands/opsx-*.md` only).
2. `STRUCTURE_HASH` = sha256 of each path followed by `"\n"` (UTF-8), in
   sorted order — **paths only**; do not fold file bytes (content stays in
   occurrence hashes / snapshot `safe_tree_hash`).
3. Persist `structure_hash` on `index-state.yaml` for the source.
4. If a previous `structure_hash` exists and differs → emit index signal
   `STRUCTURE_CHANGED` with `added_paths` / `removed_paths` (study cue:
   layout drift may expose useful commands or unexpected removals).

`STRUCTURE_CHANGED` is orthogonal to `NEW_COMPONENT` / `NEW_VARIANT` /
`COMMAND_REMOVED` content signals.

## Occurrence fields (catalog SoT)

```text
OCCURRENCE_ID
SOURCE_ID
COMPONENT_ID
COMMAND_PATH
FULL_FILE_HASH
CANONICAL_BODY_HASH
CONTRACT_HASH
COMPONENT_VERSION
ALIASES
PURPOSE
TAGS
```

## Generated views

- `by-repo/<source_id>.json`
- `by-command/<component_id>.json`
- `by-hash/<canonical_hash>.json`

## ADOPTION_PACKET (design/fix/discover → import)

```text
SOURCE_ID
PROJECTION_COMMIT
COMMAND_PATH
COMMAND_HASH
MODE: REUSE | OVERLAY | FORK
TARGET_COMMAND_ID
POST_ADOPT_ACTION: NONE | RESUME_DESIGN | RESUME_FIX
REQUIRED_COMPANIONS: []
```
