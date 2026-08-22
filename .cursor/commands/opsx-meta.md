---
component_id: opsx.commands.meta_router
component_version: 0.2.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Canonical META router for /opsx-meta-* command plane; supersedes /opsx-команда alias"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-01`  
**Runtime class:** `ACTIVE`  
Always `READ_ONLY`. Never write. Never execute recommended workers.

### Projectization / bootstrap gate

- If `.opsx/` is absent → `WHERE: NEED_BOOTSTRAP` →
  `NEXT_ACTION: /opsx-meta-bootstrap`.
- Else if `.opsx/projectization.yaml` missing or `status` != `COMPLETE` →
  `NEXT_ACTION: /opsx-projectize`.

---

# /opsx-meta

READ_ONLY orientation for the **command plane** (`/opsx-meta-*`).

Shared: `.opsx/shared/meta-orientation.md`, `.opsx/shared/command-discovery.md`

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-01
LANE: META
```

## Cheap signals (no full tree walks)

- `.opsx/` absent? → NEED_BOOTSTRAP
- local process dirty?
- `.opsx/sources.yaml` / `.opsx/lock.yaml` present?
- snapshot STATUS if configured (`CURRENT|STALE|MISSING|UNAVAILABLE`)
- index watermark vs snapshot HEAD if reachable
- pending `.tmp/opsx-*` packets / watched candidates (ids only)

## WHERE → NEXT_ACTION

| WHERE | NEXT_ACTION |
|---|---|
| NEED_BOOTSTRAP | `/opsx-meta-bootstrap` |
| NEED_PROJECTIZE | `/opsx-projectize` |
| NEED_LOCAL_COMMIT | `/opsx-meta-commit` |
| SNAPSHOT_STALE / MISSING | `/opsx-meta-update-snapshot` |
| INDEX_STALE | `/opsx-meta-update-index` |
| DISCOVERY_AVAILABLE | `/opsx-meta-discover` |
| NEED_IMPORT | `/opsx-meta-import-command` |
| NEED_DESIGN | `/opsx-meta-design-command` |
| NEED_FIX | `/opsx-meta-fix-command-defects` |
| NEED_CONSULT | `/opsx-meta-consult` |
| AMBIGUOUS | `/opsx-meta-consult` |

## Output

```text
STATUS: ORIENTED | ROUTED | AMBIGUOUS | FAIL_CLOSED
MODE: READ_ONLY
LANE: META
WHERE:
NEXT_ACTION:
ORIENTATION_HINT:
  LANE: META
  STATUS:
  NEXT_META: /opsx-meta
  NEXT_ACTION:
RECOMMENDATION_STRENGTH: advisory
```
