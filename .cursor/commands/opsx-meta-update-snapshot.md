---
component_id: opsx.commands.meta_update_snapshot
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Committed allowlist → central repo/branch snapshot Git; Owner GO"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-SNAPSHOT-01
newline_normalization: none
---

# /opsx-meta-update-snapshot

Publish **committed** allowlisted process tree (SoT: `.opsx/sources.yaml`) into
the configured `sources/<repo_family>/<branch>/` snapshot Git repo.
Same allowlist as `/opsx-meta-commit`. Product `openspec/**` / app code stay on
`/opsx-commit` and are hard-excluded from this snapshot.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-SNAPSHOT-01
WRITES: central snapshot Git only
```

Tool: `node .opsx/tools/opsx-central-catalog.mjs snapshot-plan|snapshot-apply`  
Config: `.opsx/sources.yaml`

## When to use

After `/opsx-meta-commit` when local process surfaces changed, or when snapshot
is STALE/MISSING.

## When not to use

- Local commit → `/opsx-meta-commit`
- Index update → `/opsx-meta-update-index`
- Import a command → `/opsx-meta-import-command`

## Modes

| Input | Mode | Writes |
|---|---|---|
| default | READ_ONLY plan | none (prints plan JSON) |
| exact `GO` | APPLY | snapshot working tree + commit (+ ordinary push if remote) |
| dirty allowlist without `HEAD_ONLY_CONFIRMED` | FAIL_CLOSED | none |

## Hard rules

- Copy only committed blobs for allowlisted paths.
- Never copy `.env*`, product `src/public/backend`, `node_modules`, secrets.
- Preserve snapshot `.git`; replace allowlisted files; stage deletions.
- Commit only when safe-tree/metadata delta exists.
- Never force-push. Never mutate catalog index files.
- Success ⇒ `INDEX_STATUS: STALE` and `NEXT_ACTION: /opsx-meta-update-index`.

## Steps

1. Projectization gate.
2. Require `.opsx/sources.yaml`.
3. Run `snapshot-plan`. If dirty and no `HEAD_ONLY_CONFIRMED` → stop.
4. Without `GO` → print plan and stop.
5. With `GO` → `snapshot-apply` (add `--head-only` only when Owner confirmed).
6. Emit receipt + ORIENTATION_HINT.

## Output

```text
STATUS: PLAN_READY | SNAPSHOT_UPDATED | CURRENT_NO_SAFE_DELTA | BLOCKED_DIRTY | FAIL_CLOSED
SNAPSHOT_DIR:
SOURCE_ID:
INDEX_STATUS: STALE | UNKNOWN
NEXT_ACTION:
ORIENTATION_HINT:
  LANE: META
  NEXT_META: /opsx-meta
  NEXT_ACTION:
```
