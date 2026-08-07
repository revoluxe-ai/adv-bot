---
component_id: opsx.commands.meta
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Target-native OPSX meta orientation: PRODUCT + COMMAND lanes; Owner request 2026-08-06"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority paths (read)

- Commands / rules / pipeline: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`
- OPSX shared / registry / project lock: `.opsx/shared/**`, `.opsx/registry/**`, `.opsx/projectization.yaml`, `.opsx/sources.yaml`, `.opsx/lock.yaml` (if present)
- OpenSpec process (read for PRODUCT lane hints only): `openspec/changes/**`, `openspec/evolution/**`

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not write any files in any mode (always READ_ONLY).
- Do not execute recommended `/opsx-*` workers in the same turn.
- Never PASS-by-absence; missing graph/status → honest `unknown` / route, not invented edges.

### Projectization / bootstrap gate

Before emitting a routed next action that assumes normal commands:

1. If `.opsx/` is absent:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_BOOTSTRAP_REQUIRED
NEXT_ACTION: /opsx-meta-bootstrap
```

2. Else if `.opsx/projectization.yaml` missing, `status` != `COMPLETE`, or
   `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_ACTION: /opsx-projectize
```

Exempt self-orientation toward `/opsx-projectize` and `/opsx-meta-bootstrap`.

---

# /opsx

READ_ONLY **meta-command**: orient the operator — which lane, where am I, one
pasteable next step. Shared contract: `.opsx/shared/meta-orientation.md`.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-01
MODE_FAMILY: READ_ONLY_ORIENTATION
```

## Purpose

1. Choose lane: `PRODUCT` (not-admin lifecycle) vs `COMMAND` (process/admin
   command plane).
2. Emit exactly one advisory `NEXT_ACTION`.
3. Never redesign, fix, import, commit, or navigate by rebuilding a private graph.

## Aliases / lanes

| Invoke | Lane |
|---|---|
| `/opsx` (empty / ambiguous) | detect from `$ARGUMENTS` + latest message |
| `/opsx product` / `/opsx pipeline` | `PRODUCT` |
| `/opsx meta` / `/opsx команда` / `/opsx command` | `META` → prefer `/opsx-meta` |
| `/opsx-meta` | dedicated META router |

## When to use

- “Where am I / what next?” across product **or** meta/command-plane work.
- After a meta worker printed `ORIENTATION_HINT` / `NEXT_META: /opsx-meta`.

## When not to use

- Known not-admin next step → `/opsx-pipeline`
- Known concrete meta worker → invoke `/opsx-meta-*` directly
- Relationship ambiguity → `/opsx-meta-consult`

## Lane detection

1. Explicit lane tokens win (`meta` / `команда` / `command` / `product` / `pipeline`).
2. Else if message cites `/opsx-meta-*`, process surfaces, snapshot/index/import/design/fix → route `NEXT_ACTION: /opsx-meta` (or concrete worker when clear).
3. Else if product lifecycle → `PRODUCT`.
4. Else → `AMBIGUOUS` → `/opsx-meta-consult` or one question.

## PRODUCT lane (cheap)

1. Prefer exact-path check that `.cursor/pipeline/GRAPH.md` (+ `META.md`) exist.
2. If present → `NEXT_ACTION: /opsx-pipeline`.
3. If missing → `NEXT_ACTION: /opsx-pipeline UPDATE`.
4. Emit `LANE: PRODUCT`.

## META / COMMAND lane (cheap)

Prefer handing off to `/opsx-meta` unless a single concrete worker is obvious:

| WHERE | Typical NEXT_ACTION |
|---|---|
| `NEED_BOOTSTRAP` | `/opsx-meta-bootstrap` |
| `NEED_PROJECTIZE` | `/opsx-projectize` |
| `NEED_LOCAL_COMMIT` | `/opsx-meta-commit` |
| `SNAPSHOT_STALE` | `/opsx-meta-update-snapshot` |
| `INDEX_STALE` | `/opsx-meta-update-index` |
| `NEED_DISCOVER` | `/opsx-meta-discover` |
| `NEED_IMPORT` | `/opsx-meta-import-command` |
| `NEED_FIX` | `/opsx-meta-fix-command-defects` |
| `NEED_DESIGN` | `/opsx-meta-design-command` |
| `NEED_CONSULT` | `/opsx-meta-consult` |
| `META_ORIENT` | `/opsx-meta` |

## Output contract (every run)

```text
STATUS: ORIENTED | ROUTED | AMBIGUOUS | FAIL_CLOSED | BLOCKED_NEEDS_EVIDENCE
MODE: READ_ONLY
LANE: PRODUCT | META | AMBIGUOUS
WHERE: <token or none>
NEXT_ACTION:
ORIENTATION_HINT:
  LANE: <same>
  STATUS:
  NEXT_META: /opsx | /opsx-meta
  NEXT_ACTION:
RECOMMENDATION_STRENGTH: advisory
```

For META lane, `NEXT_META` should be `/opsx-meta`.

## Anti-patterns (reject)

- Writing files / treating `GO` as apply
- Executing recommended workers in-meta
- Folding meta graph into `/opsx-pipeline` `ALL_NON_ADMIN_OPSX`
- Dumping full command catalog as “orientation”
- Multiple competing `NEXT_ACTION` lines
