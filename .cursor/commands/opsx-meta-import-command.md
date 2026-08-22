---
component_id: opsx.commands.meta_import_command
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Unified meta import: index-first + raw-donor fallback; supersedes opsx-admin-command-inbound-opsx"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-IMPORT-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-IMPORT-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority paths (local)

- Commands / rules / pipeline: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`
- OpenSpec process: `openspec/policies/**`, `openspec/schemas/**`
- OPSX shared / registry / adapters docs: `.opsx/shared/**`, `.opsx/registry/**`, `.opsx/adapters/**`
- Staging only: `.tmp/opsx-inbound/**`
- Frozen upstream (read): `.opsx/upstream/**` — **do not overwrite by default**

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not import foreign **product** dumps: `openspec/changes/**`, `openspec/archive/**`,
  product `openspec/decisions/**` content, `src/**`, `public/**`, `.env*`.
- Do not activate WB/product domain assumptions from a donor without Owner KEEP
  **and** target remapping (default disposition `SKIP_DOMAIN`).
- Do not blind-replace `.opsx/upstream/**` (`central_update_policy: NEVER_OVERWRITE`
  in `.opsx/manifest.yaml`) unless Owner explicit `KEEP=upstream-refresh` + flag.
- Never PASS-by-absence; missing donor path → `FAIL_CLOSED`.

### Projectization / bootstrap gate

1. If `.opsx/` is absent (empty / foreign repo with no OPSX tree):

```text
STATUS: FAIL_CLOSED
REASON: OPSX_BOOTSTRAP_REQUIRED
NEXT_COMMAND: /opsx-meta-bootstrap
```

2. Else read `.opsx/projectization.yaml` before any write.
   If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

---

# /opsx-meta-import-command

Sole active **command import** owner. Default source is the central catalog
index; explicit raw repo/archive donors remain supported as fallback.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-META-IMPORT-01
PRODUCT_WRITER: NO
UPSTREAM_OVERWRITE_DEFAULT: NO
DEFAULT_SCOPE: one primary command (+ demonstrated companions only)
```

Shared: `.opsx/shared/command-discovery.md`

## Purpose

Find / compare / Owner-select / materialize one coherent command packet into
this project while preserving TARGET OVERRIDE, adapter gates, lock, activation,
and provenance.

## Source modes

```text
INDEX_DEFAULT   query=<id|alias|purpose> | OCCURRENCE=<id> | ADOPTION_PACKET=<path>
RAW_DONOR       source=<repo-path|archive> [surfaces=...]
```

## When to use

- Direct “find and import this command” from central index.
- Handoff from `/opsx-meta-discover`, design, or fix (`ADOPTION_PACKET`).
- Raw donor path/archive not yet indexed (`source=`).

## When not to use

- No `.opsx/` / empty-repo first contact → `/opsx-meta-bootstrap`
- Surfaces staged but lock not COMPLETE → `/opsx-projectize`
- Adapter/capability refresh only → `/opsx-adapt-project`
- Change delta specs → main specs → `/opsx-sync`
- Local command-contract wording defect → `/opsx-meta-fix-command-defects`
- Cheap command-plane “where next?” → `/opsx-meta`
- Unsure which meta command → `/opsx-meta-consult`
- Product / game feature work → `/opsx-explore` and product lifecycle
- Blind refresh of frozen `.opsx/upstream/**` (default forbidden)

## Authority boundary

- Default mode is **READ_ONLY** (compare + advise). Writes only on exact `GO`
  with a usable `DIFF_PACKET` and non-empty approved `KEEP`.
- Does **not** own product OpenSpec changes/decisions/archive.
- Does **not** re-open projectization lock or replace `/opsx-projectize:GO`.
- Does **not** own adapter capability invention (handoff to adapt-project after merge).
- Does **not** commit (handoff `/opsx-meta-commit`).
- Decision owner for KEEP / SKIP / CONFLICT resolution: **Owner**.

## User input

```text
$ARGUMENTS
```

### Parameters

| Token | Required | Meaning |
|---|---|---|
| `query=` / `OCCURRENCE=` / `ADOPTION_PACKET=` | INDEX_DEFAULT | Resolve candidate from fresh catalog index (preferred) |
| `source=<path>` | RAW_DONOR | Absolute or repo-relative donor checkout **or** extracted archive root |
| `surfaces=` | no | Comma list; default `commands,rules,pipeline,openspec-process,opsx-shared` |
| `packet=<path>` | GO | Path to prior `DIFF_PACKET.md` under `.tmp/opsx-inbound/` (or chat-attached equivalent) |
| `KEEP=<ids>` | GO | Comma list of row ids / command ids / relative paths from the packet to merge |
| `GO` | APPLY | Exact apply token |

Empty invoke without index selector and without `source=` / clear donor →
`BLOCKED_NEEDS_EVIDENCE` (ask once for `query=` / `OCCURRENCE=` / `source=`).

## Modes

| Input | Mode | Writes |
|---|---|---|
| no `GO` | `READ_ONLY` | staging under `.tmp/opsx-inbound/<UTC>/` allowed for DIFF_PACKET / ADOPTION_PACKET only |
| exact `GO` + packet + KEEP | `APPLY` | approved process files + MERGE_RECEIPT + lock/activation/provenance as needed |
| `GO` without packet or KEEP | `FAIL_CLOSED` | none |

## Surfaces compared (default)

Donor vs local, when present:

| Surface key | Paths (relative to donor / local root) |
|---|---|
| `commands` | `.cursor/commands/opsx-*.md` |
| `rules` | `.cursor/rules/**` (opsx / architecture / documentation / process) |
| `pipeline` | `.cursor/pipeline/**` |
| `openspec-process` | `openspec/policies/**`, `openspec/schemas/**` |
| `opsx-shared` | `.opsx/shared/**` |

**Never compared for merge (hard reject on GO):** donor `openspec/changes/**`,
`openspec/archive/**`, product decision dumps, `src/**`, `public/**`, secrets.

## Classification (every delta row)

| Kind | Meaning |
|---|---|
| `NEW_COMMAND` | Donor has `opsx-*` command id local lacks |
| `UPDATED_COMMAND` | Same command id; body/version/hash differs |
| `STRUCTURE_DELTA` | Schema/policy/pipeline layout differs |
| `LOCAL_ONLY` | Local has; donor lacks (informational) |
| `SKIP_DOMAIN` | WB / Poetry / kubectl / foreign product assumptions without target adapter |
| `CONFLICT` | Both evolved; default keep local until Owner picks |

### Advice dispositions (mandatory on each actionable row)

| Disposition | Meaning |
|---|---|
| `USEFUL_CANDIDATE` | Likely helps this WB Sky / Poetry target after remapping |
| `SKIP_DOMAIN` | Harmful or wrong domain; do not merge |
| `SKIP_DUPLICATE` | Already covered locally |
| `CONFLICT_LOCAL_WINS_DEFAULT` | Diverged; keep local unless Owner KEEP |
| `CONFLICT_NEEDS_OWNER` | Owner must choose before GO |
| `STRUCTURE_DELTA` | Layout/policy change; evaluate separately |

## Steps — READ_ONLY (INDEX_DEFAULT)

1. Projectization gate (read). If not COMPLETE → `FAIL_CLOSED`.
2. Read `.opsx/shared/command-discovery.md` freshness rules. Resolve index via
   `.opsx/sources.yaml` / `.opsx/lock.yaml`. If index STALE/MISSING and no
   Owner `LOCAL_ONLY_CONFIRMED` → `BLOCKED_NEEDS_FRESH_INDEX` →
   `NEXT_ACTION: /opsx-meta-update-index`.
3. Resolve candidate from `ADOPTION_PACKET=` (preferred handoff), else
   `OCCURRENCE=`, else `query=` against by-command / by-hash / by-repo views.
4. Materialize a bounded compare of the selected occurrence (and listed
   companions) vs local — do **not** merge. Write staging
   `.tmp/opsx-inbound/<UTC>/` with `SOURCE.txt`, `ADOPTION_PACKET.md` (echo),
   and `DIFF_PACKET.md`.
5. Emit output contract. Owner must approve KEEP before GO.

## Steps — READ_ONLY (RAW_DONOR fallback)

1. Projectization gate (read). If not COMPLETE → `FAIL_CLOSED`.
2. Resolve `source=`. If missing → `BLOCKED_NEEDS_EVIDENCE`.
3. Confirm donor root looks like OPSX (at least one of: `.cursor/commands`,
   `openspec/policies`, `.opsx`). Else `FAIL_CLOSED` `REASON: NOT_OPSX_SURFACE`.
4. Create staging dir `.tmp/opsx-inbound/<UTC>/` and write `SOURCE.txt`
   (resolved path + optional git short SHA if `.git` present — best effort).
5. Inventory donor vs local for selected `surfaces=` (filename / id inventory
   first; content hash or bounded section compare for UPDATED rows).
   Follow `.cursor/commands/opsx-execution-preflight.md` I/O budgets:
   Grep-first; parallel Read max 2; no full dump of every command body unless
   needed for a CONFLICT/UPDATED row.
6. Classify each row; fill USEFUL / SKIP / CONFLICT advice with one-line why.
7. Write `DIFF_PACKET.md` into the staging dir (required durable artifact).
8. Emit output contract. Do **not** merge. Do **not** touch live process files
   beyond the staging packet.

## Steps — APPLY (`GO`)

1. Projectization gate again.
2. Require exact token `GO`.
3. Load `packet=` (or newest `.tmp/opsx-inbound/*/DIFF_PACKET.md` only if
   unambiguous in this chat). Missing → `FAIL_CLOSED`.
4. Require non-empty `KEEP=` (ids from packet). Empty KEEP → `FAIL_CLOSED`.
5. Validate every KEEP target is inside the write boundary. Any forbidden path
   → `FAIL_CLOSED`, no writes.
6. For each KEEP item:
   - **NEW_COMMAND:** create `.cursor/commands/<name>.md` as target-native:
     TARGET OVERRIDE header + remapped body (strip WB/Poetry/kubectl execution
     into UNAVAILABLE / FAIL_CLOSED; do not invent adapters).
   - **UPDATED_COMMAND:** merge donor improvements into local file **preserving**
     existing TARGET OVERRIDE / `local_modification_note` / contract_id unless
     Owner KEEP explicitly replaces them.
   - **STRUCTURE / shared / policy:** copy or merge only listed relative paths;
     never wipe local product specs.
7. Update `.opsx/registry/command_activation.ndjson` and provenance row for
   newly installed commands. Update `.opsx/lock.yaml` stub entries when the
   adopted command is lock-tracked.
8. Write `MERGE_RECEIPT.md` under the same staging dir.
9. Emit output contract with `STATUS: MERGE_APPLIED`.
10. Suggest next: `/opsx-adapt-project` if activation/gates may need refresh;
    then `/opsx-meta-commit` for process commits. Do **not** commit here.
    Do **not** run snapshot/index update (separate owners).

## Merge safety rules

1. Preserve local `TARGET OVERRIDE — HIGHEST PRIORITY` blocks.
2. Default disposition for domain foreign content: `SKIP_DOMAIN`.
3. Never overwrite `.opsx/upstream/**` unless Owner `KEEP` includes explicit
   upstream-refresh flag documented in the packet.
4. Never write `openspec/changes/**`, `openspec/archive/**`, or product
   `openspec/decisions/**` from donor.
5. Do not run `/opsx-projectize:GO` as part of this command.
6. Partial failure mid-KEEP → stop; report applied vs skipped; do not pretend
   full success.

## Output contract (every run)

```text
STATUS:
MODE: READ_ONLY | APPLY
WHAT_HAPPENED:
WHY:
SOURCE:
STAGING_DIR:
DIFF_SUMMARY:
USEFUL_CANDIDATES:
SKIP:
CONFLICTS:
KEEP_APPLIED: none | <list>
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
ORIENTATION_HINT:
  LANE: COMMAND
  STATUS: <same as STATUS>
  NEXT_META: /opsx-meta
  NEXT_ACTION: <same as NEXT_ACTION>
```

Meta: `/opsx` / `/opsx-meta`. See `.opsx/shared/meta-orientation.md`.

### STATUS values

```text
DIFF_PACKET_READY
MERGE_APPLIED
BLOCKED_NEEDS_EVIDENCE
BLOCKED_NEEDS_FRESH_INDEX
FAIL_CLOSED
```

### Field meaning

- `DIFF_SUMMARY` — counts by kind (NEW / UPDATED / STRUCTURE / LOCAL_ONLY / …)
- `USEFUL_CANDIDATES` — short table: id → why useful on this target
- `SKIP` — id → why not
- `CONFLICTS` — id → what Owner must choose
- `KEEP_APPLIED` — only in APPLY; list of merged ids
- `NEXT_ACTION` — one pasteable line (e.g. GO with KEEP, or adapt-project, or commit)

## DIFF_PACKET.md minimum sections

```markdown
# DIFF_PACKET
UTC:
SOURCE:
LOCAL_HEAD: (best effort)
SURFACES:

## Rows
| id | kind | disposition | donor_path | local_path | why |

## Recommended KEEP (suggestion only)
- …

## Forbidden (hard)
- …
```

## Human workflow tokens

```text
WHAT_HAPPENED: …
WHY: …
CURRENT_STATE: DIFF_PACKET_READY | MERGE_APPLIED | …
OWNER_DECISION_REQUIRED: approve KEEP set | none
NEXT_ACTION: …
DO_NOT_DO_YET: …
```

## Failure / recovery

| Condition | STATUS | Recovery |
|---|---|---|
| `.opsx/` absent | FAIL_CLOSED | `/opsx-meta-bootstrap` |
| projectization not COMPLETE | FAIL_CLOSED | `/opsx-projectize` |
| missing query/occurrence/source | BLOCKED_NEEDS_EVIDENCE | provide `query=` / `OCCURRENCE=` / `source=` |
| stale/missing index | BLOCKED_NEEDS_FRESH_INDEX | `/opsx-meta-update-index` |
| not an OPSX tree | FAIL_CLOSED | fix path / extract archive |
| GO without packet/KEEP | FAIL_CLOSED | re-run compare; pass KEEP |
| KEEP hits forbidden path | FAIL_CLOSED | narrow KEEP |
| post-merge contract awkward | MERGE_APPLIED + note | `/opsx-meta-fix-command-defects` |

## Regression checks (implementer / operator)

- [ ] READ_ONLY never writes outside `.tmp/opsx-inbound/**`
- [ ] GO without KEEP fails closed
- [ ] Cannot write product changes/decisions/src
- [ ] TARGET OVERRIDE preserved on UPDATED merges
- [ ] Default does not touch `.opsx/upstream/**`
- [ ] consult routes foreign-OPSX / central-reuse questions here
- [ ] INDEX_DEFAULT preferred; RAW_DONOR only as fallback
- [ ] APPLY updates activation + lock stub; never snapshot/index
