---
component_id: opsx.commands.meta_export_pack
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Projectize 2026-08-07: remapped Vue/npm → poetry-python / WB Sky; opsx-lite only"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-EXPORT-PACK-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-EXPORT-PACK-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority / export roots

- Process: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`, …
- OpenSpec static: `openspec/config.yaml`, `policies`, `schemas`, `specs`, `decisions`, `tools`
- Project-local OPSX: `.opsx/adapters/**`, `.opsx/registry/**`, `.opsx/shared/**`,
  `.opsx/project/**`, `.opsx/import/**`, `.opsx/manifest.yaml`, `.opsx/projectization.yaml`
- Export writes **only**: `.tmp/opsx-export/<utc_ts>/`

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not delete/move/rename **source** trees (copy-only).
- Do not expand allowlist into `src/**`, `public/**`, `backend/` app code,
  `.env*`, or secrets.
- Do not include `.opsx/upstream/**` unless Owner passes
  `include_upstream_snapshot` (large frozen snapshot).
- Never PASS-by-absence.

### Projectization gate

Read `.opsx/projectization.yaml` before any write under `.tmp/opsx-export/`.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

---

# /opsx-meta-export-pack

Side-lane **copy-only** utility: collect allowlisted OPSX / OpenSpec surfaces into
a new zip under `.tmp/opsx-export/<utc_ts>/`, print the **absolute** archive path,
and leave every source tree untouched.

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-WB-EXPORT-PACK-01
MODE_FAMILY: COPY_ONLY
```

This is **not** `/opsx-archive` (lifecycle move/promote of a completed change).
This is **not** `/opsx-doctor` (may delete leftovers).
This is **not** `/opsx-meta-import-command` (compare/merge foreign pack).
This is **not** a commit path (export artifacts stay out of git).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including Read / tool I/O budgets).

## Purpose

1. Give the human one portable pack of **this repo’s** OPSX process + OpenSpec SoT
   (including project-local `.opsx` adapters/registry — not only `.cursor/`).
2. Reduce ad-hoc zips under `.cursor/` (junk that must not be committed).
3. Guarantee **no delete / no move / no rename** of sources — even if the user
   types `GO`, `cleanup`, or `delete`.

## When to use

- Need a shareable / offline / backup snapshot of local OPSX commands + specs.
- Preparing inbound into another fork / external review without cloning.
- Publish a `BOOTSTRAP_PROFILE` pack for `/opsx-meta-bootstrap`
  (`scope=bootstrap_profile`) into central `bootstrap/profile/` (Owner copy).
- After consult routes «нужен dump OPSX» here.

## When not to use

- Archive a completed OpenSpec change → `/opsx-archive`
- Commit process surfaces → `/opsx-meta-commit`
- Compare/merge a foreign OPSX zip → `/opsx-meta-import-command`
- Delete corrupt leftover changes → `/opsx-doctor` (if installed)
- Day-to-day navigate → `/opsx-pipeline`
- Product code / app dump → out of scope (refuse)

## User input

```text
$ARGUMENTS
```

Optional tokens:

| Token | Meaning |
|---|---|
| `scope=default` | process + openspec static + project-local `.opsx` (default) |
| `scope=process` | process surfaces only (`.cursor/**` allowlist + AGENTS mirrors) |
| `scope=openspec` | openspec static SoT only |
| `scope=opsx` | project-local `.opsx` allowlist only |
| `scope=bootstrap_profile` | only paths listed in `.opsx/shared/bootstrap-profile.md` (for central `bootstrap/profile/` publish) |
| `scope=all_safe` | same as default (alias; still bounded) |
| `include_active_changes` | also copy `openspec/changes/*` active roots (not archive/) |
| `include_archived_changes` | also copy `openspec/changes/archive/**` (can be large) |
| `include_upstream_snapshot` | also copy `.opsx/upstream/**` (large; opt-in) |

Unrecognized tokens that request delete/cleanup/rm → `REFUSED_DELETE_REQUEST`.

## Modes

| Input | Mode | Writes |
|---|---|---|
| default / any scope flags | `COPY_ONLY` | **only** new files under `.tmp/opsx-export/<utc_ts>/` |
| `GO` | ignored for extra power | same — still COPY_ONLY; never delete |
| delete / cleanup / rm requests | refuse | **no** writes that remove anything |

There is **no** delete gate. `GO` does not authorize deletion.

## Hard boundaries (mandatory)

MUST NOT:

- delete, unlink, truncate, move, or rename any source path;
- `git clean`, `git reset --hard`, or overwrite existing export dirs;
- write outside `.tmp/opsx-export/<utc_ts>/`;
- stage or commit the zip;
- expand allowlist into `src/`, `public/`, `backend/` application code, `.env*`,
  secrets, or IDE prefs (`.cursor/settings.json`);
- substitute for `/opsx-archive` lifecycle;
- claim verify / archive / commit readiness from this utility.

MUST:

- create a **new** timestamped directory every run;
- copy files into that directory (or stream into zip) without mutating sources;
- emit Windows-style absolute path to the zip when on Windows;
- skip `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/`, and other
  obvious junk dirs when walking trees;
- if a requested include tree is missing → note in MANIFEST / EXCLUDED, continue
  (do not fail the whole pack unless **zero** include roots exist).

## Default allowlist (`scope=default`)

### Process surfaces (same family as admin-commit)

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Skip under these trees: archives/junk already present (e.g. `commands.zip`),
`__pycache__/`, `*.pyc`, `node_modules/`.

### Project-local OPSX (WB Sky / Poetry)

```text
.opsx/adapters/**
.opsx/registry/**
.opsx/shared/**
.opsx/project/**
.opsx/import/**
.opsx/manifest.yaml
.opsx/projectization.yaml
```

Default **exclude**: `.opsx/upstream/**` (opt-in via `include_upstream_snapshot`).

### OpenSpec static SoT

```text
openspec/config.yaml
openspec/specs/**
openspec/decisions/**
openspec/evolution/**
openspec/policies/**
openspec/schemas/**
openspec/tools/**
```

(Missing roots → EXCLUDED note; do not invent.)

### Bootstrap profile (`scope=bootstrap_profile`)

Copy **only** paths listed in `.opsx/shared/bootstrap-profile.md`
(`BOOTSTRAP_PROFILE` + do not include hard excludes). Prefer zip name
`opsx-bootstrap-profile.zip`. Owner may place the result under central
`bootstrap/profile/` for `/opsx-meta-bootstrap central=…` consumers.

Missing shared contract → `FAIL_CLOSED` `REASON: BOOTSTRAP_PROFILE_CONTRACT_MISSING`.

### Optional (off by default)

```text
include_active_changes     → openspec/changes/<active>/  (not archive/)
include_archived_changes   → openspec/changes/archive/**
include_upstream_snapshot  → .opsx/upstream/**
```

Never include: `openspec/changes/**/__pycache__`, binary Job artifacts, secrets.

## Pipeline position

```text
ENTRY_STATE: any (repo with allowlisted trees)
PREVIOUS_ALLOWED_STEP: /opsx-meta-consult route | direct invoke
COMMAND_ACTION: copy allowlisted paths → new zip; emit ABSOLUTE_ARCHIVE_PATH
EXIT_STATE: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST | FAIL_CLOSED
NEXT_ALLOWED_STEP: human uses path; /opsx-meta-bootstrap central=<zip|dir> on empty peer; /opsx-meta-import-command on peer; consult/pipeline
FAILURE_OR_RECOVERY_STEP: leave partial export dir; never delete sources; re-run (new ts)
```

## Steps

1. Projectization gate (read). If not COMPLETE → `FAIL_CLOSED`.
2. Parse `$ARGUMENTS`. If delete/cleanup/rm intent →
   `STATUS: REFUSED_DELETE_REQUEST`, stop, no writes.
3. Resolve `scope` (default=`default`) and optional include flags.
4. Build include-root list from allowlist; verify at least one root exists.
5. Create `.tmp/opsx-export/<utc_ts>/` (utc like `20260805-191530`).
6. Copy allowlisted trees into a staging folder **or** add directly to zip
   with stable relative paths from repo root. Prefer zip name:
   `opsx-pack.zip`.
7. Write `MANIFEST.txt` beside the zip listing:
   - utc_ts, scope, include flags, root paths included, skip patterns,
   - file count / approximate size if cheap.
8. Compute absolute path to `opsx-pack.zip` (Windows: full `C:\...` path).
9. Return output contract. Do **not** stage, commit, push, or delete sources.

### Implementation notes (agent)

- Prefer PowerShell/`Compress-Archive`, `zip`, or Python zipfile; bash on this
  repo is fine if paths are correct and sources untouched.
- Never `rm -rf` staging of **sources**. Staging under the new export dir may
  be left as-is after zip; do not delete source trees to “clean up”.
- Cleaning the export staging folder after zip is **optional** and only allowed
  **inside** the new `.tmp/opsx-export/<utc_ts>/` directory created this run —
  never outside it. Prefer leaving staging + zip both present if unsure.
- Time-budget large `include_archived_changes` / `include_upstream_snapshot`
  walks; on hang → `BLOCKED_IO`.

## Output contract

```text
STATUS: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST | FAIL_CLOSED
MODE: COPY_ONLY
COMMAND: /opsx-meta-export-pack

EXPORT_PACK_RECEIPT:
- utc_ts:
- scope:
- include_active_changes: true|false
- include_archived_changes: true|false
- include_upstream_snapshot: true|false
- absolute_archive_path:
- manifest_path:
- roots_included: [paths]
- excluded_or_skipped: [notes]
- delete_performed: false

WHAT_HAPPENED:
WHY:
OWNER_DECISION_REQUIRED: none | <scope choice>
NEXT_ACTION:
DO_NOT_DO_YET:
- do not commit the zip (/opsx-meta-commit will refuse)
- do not treat this as /opsx-archive
- do not ask this command to delete anything
ORIENTATION_HINT:
  LANE: COMMAND
  STATUS: <same as STATUS>
  NEXT_META: /opsx-meta
  NEXT_ACTION: <same as NEXT_ACTION>
```

Meta: `/opsx` / `/opsx-meta`. See `.opsx/shared/meta-orientation.md`.

`NEXT_ACTION` after success is usually `none` (pack is ready) or
`/opsx-meta-import-command source=<path>` on a peer, or
`/opsx-meta-commit` **only** if process command files were edited in
the same chat for other reasons — never to commit the zip.

## Failure / recovery

| Condition | STATUS | NEXT |
|---|---|---|
| projectization not COMPLETE | `FAIL_CLOSED` | `/opsx-projectize` |
| No allowlisted roots exist | `BLOCKED_NEEDS_INPUT` | confirm cwd / repo |
| I/O / zip failure | `BLOCKED_IO` | report path attempted; leave partial; re-run |
| User asked delete | `REFUSED_DELETE_REQUEST` | explain ban; offer re-run copy-only |
| Ambiguous scope | `BLOCKED_NEEDS_INPUT` | ask one scope question |

## Authority

- Owns: copy-only export pack contents via allowlist + absolute path receipt.
- Does **not** own: change archive, doctor deletes, process commits, verify, inbound merge.
- Companion: `/opsx-meta-commit` must keep export zips OUT_OF_SCOPE.
- Peer: `/opsx-meta-import-command` consumes packs produced here (or equivalents).

## Anti-patterns

- Naming or describing this as “archive the change”
- Deleting old `.tmp/opsx-export/*` “to save space” from this command
- Dumping whole monorepo / `src/` / `public/`
- Committing `opsx-pack.zip` into `.cursor/`
- Using `GO` to unlock delete
- Default-including `.opsx/upstream/**` without opt-in

## Self-review checklist

Before returning:

- [ ] `delete_performed: false`
- [ ] Writes only under this run’s `.tmp/opsx-export/<utc_ts>/`
- [ ] `absolute_archive_path` is absolute and clickable/copyable
- [ ] Not confused with `/opsx-archive` or `/opsx-meta-import-command`
- [ ] Allowlist not expanded into product/secrets
- [ ] `.opsx` adapters/registry included on `scope=default` when presentcomponent_version: 0.2.1
local_modification_note: "Projectize 2026-08-07: remapped Vue/npm → poetry-python / WB Sky; opsx-lite only. 2026-08-10: EXP-01/02 write-root + full discovery + ROOT_COVERAGE; EXP-03 one export = opsx-export/<utc_ts>/{opsx-pack.zip, MANIFEST.txt} + absolute_export_dir_path."
- Process: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`,
  `.cursor/devops/**`, … (explicit process allowlist; safety bound)
- OpenSpec tree: entire `openspec/**` present on disk (auto-discovers new
  top-level children, including `changes/**` and `changes/archive/**`)
- Project-local OPSX: entire `.opsx/**` present on disk (auto-discovers new
  top-level children, including `upstream/**` when present)
- Runtime packets: `.tmp/**` (on `scope=default` / `scope=tmp` / `scope=all_safe`)
- Export writes **only**: `opsx-export/<utc_ts>/` under repo-root `opsx-export/`
  (one run = one dated folder; separate from `.tmp`)
- Do not expand into `src/**`, `public/**`, `backend/` app code, `.env*`,
  or secrets (process allowlist stays bounded; `.opsx/**` + `openspec/**`
  are the only whole-tree discovery roots).
- Do not copy `opsx-export/**` into the pack (write-root; nesting ban).
Read `.opsx/projectization.yaml` before any write under `opsx-export/`.
Side-lane **copy-only** utility: collect OPSX process surfaces + **entire**
`.opsx/**` + **entire** `openspec/**` (+ `.tmp` on default) into a **new**
dated folder `opsx-export/<utc_ts>/` containing exactly `opsx-pack.zip` +
`MANIFEST.txt`, print the **absolute folder path** (primary handoff) plus zip/
manifest paths and a **ROOT_COVERAGE** report, and leave every source tree
untouched.
`GO` is **optional**. Empty invoke (no args) runs the same COPY_ONLY pack.
1. One command dump of **this repo’s** OPSX process + full project-local `.opsx`
   + full OpenSpec tree (including active/archived changes and **new** top-level
   folders under `.opsx/` / `openspec/` without updating a frozen subpath list)
   plus local `.tmp` runtime packets (except the export write-root).
4. Tell the Owner per **root folder** what was FULLY_INCLUDED vs SKIPPED.
5. Keep runs isolated: **1 export = 1 dated folder** with exactly two files
   (zip + manifest) so Owner can share that folder without mixing runs.
- Need a shareable / offline / backup snapshot of local OPSX + OpenSpec
  (+ `.tmp` packets on default scope).
Empty `$ARGUMENTS` is valid and runs `scope=default` COPY_ONLY (no `GO` required).
| `scope=default` | process allowlist + **entire** `.opsx/**` + **entire** `openspec/**` + `.tmp/**` (HARD skip `opsx-export/**`) |
| `scope=process` | process surfaces only (`.cursor/**` allowlist + AGENTS mirrors; no `.tmp`) |
| `scope=openspec` | entire `openspec/**` only (discovered top-level children) |
| `scope=opsx` | entire `.opsx/**` only (discovered top-level children) |
| `scope=tmp` | `.tmp/**` only (HARD skip `opsx-export/**`) |
| `scope=bootstrap_profile` | only paths listed in `.opsx/shared/bootstrap-profile.md` (for central `bootstrap/profile/` publish; no `.tmp`) |
| `scope=all_safe` | same as default (alias; still bounded — no product `src/`) |
| `GO` | optional; same COPY_ONLY as empty invoke — never unlocks delete |
| `include_active_changes` | **no-op on default/all_safe/openspec** (already included when path exists) |
| `include_archived_changes` | **no-op on default/all_safe/openspec** (already included when path exists) |
| `include_upstream_snapshot` | **no-op on default/all_safe/opsx** (already included when path exists) |
| empty args / any scope flags | `COPY_ONLY` | **only** new files under `opsx-export/<utc_ts>/` |
| `GO` | optional synonym | same — still COPY_ONLY; never delete |
There is **no** delete gate. `GO` does not authorize deletion. Empty invoke
does **not** mean read-only — it runs the pack.
- `git clean`, `git reset --hard`, or overwrite an existing dated export dir;
- write outside `opsx-export/<utc_ts>/` (except creating parent `opsx-export/`);
- stage or commit the zip / manifest / export dir;
- expand into `src/`, `public/`, `backend/` application code, `.env*`,
- claim verify / archive / commit readiness from this utility;
- claim `FULLY_INCLUDED` for a missing root path;
- dump many runs as flat siblings under `opsx-export/` without a dated subdir.
- ensure repo-root `opsx-export/` exists (create if missing);
- create a **new** per-run directory `opsx-export/<utc_ts>/`
  (`utc_ts` like `20260805-191530`); if it already exists → new `utc_ts` or
  `BLOCKED_IO` (never overwrite);
- inside that directory write exactly:
  - `opsx-pack.zip` (default scopes; bootstrap: `opsx-bootstrap-profile.zip`)
  - `MANIFEST.txt`
  Isolation is the **folder** name; keep inner names simple for handoff;
- on `scope=default` / `all_safe` / `opsx` / `openspec`: **discover** actual
  top-level children under `.opsx/` and/or `openspec/` each run (new
  structures included automatically);
- copy files into zip without mutating sources;
- emit Windows-style **absolute path to the export folder** as the primary
  handoff (`absolute_export_dir_path`), plus absolute zip and manifest paths;
- HARD skip `opsx-export/**` from pack contents (write-root; nesting ban);
- emit `ROOT_COVERAGE` listing every considered root folder as
  `FULLY_INCLUDED` or `SKIPPED` with reason;
- if a requested include tree is missing → `SKIPPED (missing)` in
  ROOT_COVERAGE / EXCLUDED, continue (do not fail the whole pack unless
  **zero** include roots exist).
## Default pack contents (`scope=default`)
### Process surfaces (explicit allowlist — safety bound)
.cursor/devops/**
`__pycache__/`, `*.pyc`, `node_modules/`. Never include `.cursor/settings.json`.
### Project-local OPSX — whole tree (auto-discover)
.opsx/**
Enumerate **actual** top-level children of `.opsx/` each run (dirs and files).
New top-level names are included without editing this command. Includes
`.opsx/upstream/**` when present. Root files such as `manifest.yaml`,
`projectization.yaml`, `lock.yaml`, `sources.yaml` are included.
### OpenSpec — whole tree (auto-discover)
openspec/**
Enumerate **actual** top-level children of `openspec/` each run. Includes
`openspec/changes/**` (active) and `openspec/changes/archive/**` when present,
plus any new top-level folder/file. Still skip junk patterns inside.
### Runtime packets (`.tmp`) — on `scope=default` / `scope=tmp` / `scope=all_safe`
.tmp/**
HARD **exclude** (always, any scope that walks trees): `opsx-export/**` —
this command’s write-root at repo root; never nest prior export zips into a
new pack. `opsx-export/**` is **not** an include root; always
`SKIPPED (write-root nesting ban)` in ROOT_COVERAGE.
Optional note for legacy leftovers under `.tmp/opsx-export/**` is OK;
that path is **not** this command’s write-root anymore.
Skip under `.tmp` walks: `__pycache__/`, `*.pyc`, `.pytest_cache/`,
`node_modules/`, and other obvious junk dirs.
`scope=process` / `scope=openspec` / `scope=opsx` / `scope=bootstrap_profile`
do **not** include `.tmp`. Use `scope=default` (or `scope=all_safe`) for the
full pack, or `scope=tmp` for runtime packets only.
(`BOOTSTRAP_PROFILE` + do not include hard excludes). Same per-run layout:
`opsx-export/<utc_ts>/opsx-bootstrap-profile.zip` + `MANIFEST.txt`. Owner may
place the result under central `bootstrap/profile/` for
`/opsx-meta-bootstrap central=…` consumers.
### Legacy include flags (no-op on full scopes)
include_active_changes     → no-op when openspec tree is in scope (already included)
include_archived_changes   → no-op when openspec tree is in scope (already included)
include_upstream_snapshot  → no-op when .opsx tree is in scope (already included)
Never include: secrets, product app trees, `opsx-export/**`,
`openspec/changes/**/__pycache__`, binary Job artifacts under junk skips.
## ROOT_COVERAGE (mandatory)
After the pack, receipt + `MANIFEST.txt` (inside the dated export dir) MUST
list root folders:
**Must cover at least:**
- each top-level child under `.opsx/` (when `.opsx` is in scope)
- each top-level child under `openspec/` (when `openspec` is in scope)
- each process allowlist root that was considered
- `.tmp` (when in scope)
- `opsx-export` (always listed as SKIPPED write-root)
**Statuses:**
| Status | Meaning |
| `FULLY_INCLUDED` | root exists and was walked into the pack (junk skip patterns only) |
| `SKIPPED` | not packed — reason required: `missing` \| `write-root nesting ban` \| `out of scope` \| `hard exclude` |
Do not invent roots that were never considered. Do not mark missing paths
`FULLY_INCLUDED`.
Example shape:
ROOT_COVERAGE:
- .opsx/adapters: FULLY_INCLUDED
- .opsx/upstream: SKIPPED (missing)
- openspec/changes: FULLY_INCLUDED
- openspec/specs: FULLY_INCLUDED
- .tmp: FULLY_INCLUDED
- opsx-export: SKIPPED (write-root nesting ban)
- .cursor/agents: SKIPPED (missing)
ENTRY_STATE: any (repo with include roots)
COMMAND_ACTION: create opsx-export/<utc_ts>/{opsx-pack.zip, MANIFEST.txt}; emit absolute_export_dir_path + ROOT_COVERAGE
NEXT_ALLOWED_STEP: human uses folder path; /opsx-meta-bootstrap central=<zip|dir> on empty peer; /opsx-meta-import-command on peer; consult/pipeline
FAILURE_OR_RECOVERY_STEP: leave partial artifacts under opsx-export/<utc_ts>/; never delete sources; re-run (new ts)
2. Parse `$ARGUMENTS` (may be empty). If delete/cleanup/rm intent →
   `GO` is optional and ignored for extra power.
3. Resolve `scope` (default=`default`). Legacy include_* flags are no-ops on
   scopes that already walk full `.opsx` / `openspec` trees.
4. Build include-root list:
   - process allowlist roots (when scope includes process);
   - discover top-level children of `.opsx/` (when scope includes opsx);
   - discover top-level children of `openspec/` (when scope includes openspec);
   - `.tmp` when scoped.
   Verify at least one existing root. Always HARD skip `opsx-export/**`.
5. Ensure repo-root `opsx-export/` exists. Compute `utc_ts`
   (utc like `20260805-191530`). Create **new** dir `opsx-export/<utc_ts>/`
   (`exist_ok=False`). If exists → new `utc_ts` or `BLOCKED_IO`.
6. Copy trees into zip at `opsx-export/<utc_ts>/opsx-pack.zip` with stable
   relative paths from repo root (bootstrap: `opsx-bootstrap-profile.zip` in
   the same dir). Do not overwrite.
7. Write `opsx-export/<utc_ts>/MANIFEST.txt` listing:
   - utc_ts, scope, include_tmp, whether discovery mode was used,
   - ROOT_COVERAGE (FULLY_INCLUDED / SKIPPED + reason),
   - skip patterns (must list `opsx-export/**`),
8. Compute absolute Windows paths:
   - `absolute_export_dir_path` → `…\opsx-export\<utc_ts>\` (**primary**)
   - `absolute_archive_path` → `…\opsx-pack.zip`
   - `manifest_path` → `…\MANIFEST.txt`
9. Return output contract including ROOT_COVERAGE and the folder path. Do
   **not** stage, commit, push, or delete sources.
- Never `rm -rf` staging of **sources**. Never delete prior dated export dirs.
- Prefer leaving `opsx-pack.zip` + `MANIFEST.txt` both present in the new dir.
- When walking any tree, do not follow/copy into `opsx-export/**`.
- Discovery: `Path('.opsx').iterdir()` / `Path('openspec').iterdir()` — do not
  require a frozen subpath list for those two roots.
- Time-budget large `.tmp` / large `openspec/changes/archive` /
  `.opsx/upstream` walks; on hang → `BLOCKED_IO`.
- Legacy flat files already under `opsx-export/*.zip` from older runs are left
  untouched (this command never deletes them).
- include_tmp: true|false
- discovery_opsx: true|false
- discovery_openspec: true|false
- absolute_export_dir_path:   # PRIMARY handoff — share this folder (2 files inside)
- ROOT_COVERAGE:
  - <root>: FULLY_INCLUDED | SKIPPED (<reason>)
- excluded_or_skipped: [notes; must mention opsx-export/** nesting ban]
| No include roots exist | `BLOCKED_NEEDS_INPUT` | confirm cwd / repo |
- Owns: copy-only export pack contents via discovery + process allowlist +
  absolute path receipt + ROOT_COVERAGE.
- Deleting old `opsx-export/*` “to save space” from this command
- Nesting prior `opsx-export/**` contents into a new pack
- Writing under `.tmp/opsx-export/` again (legacy; write-root is repo-root
  `opsx-export/`)
- Flat multi-run dump under `opsx-export/` without `opsx-export/<utc_ts>/`
- Omitting `absolute_export_dir_path` from the receipt
- Committing dated packs into `.cursor/` or `opsx-export/` via process commit
- Requiring `GO` before a default pack will run
- Omitting `openspec/changes/**` or new `.opsx`/`openspec` top-level children
  from default while claiming a full dump
- Omitting ROOT_COVERAGE or marking missing roots FULLY_INCLUDED
- Expanding discovery beyond `.opsx/**` + `openspec/**` into product trees
- [ ] Empty invoke or `GO` both run COPY_ONLY (GO optional)
- [ ] Writes only under new `opsx-export/<utc_ts>/`
- [ ] That dir contains `opsx-pack.zip` (or bootstrap zip) + `MANIFEST.txt`
- [ ] `absolute_export_dir_path` is absolute and is the primary handoff
- [ ] `absolute_archive_path` and `manifest_path` are absolute
- [ ] Not expanded into product/secrets / `.cursor/settings.json`
- [ ] On default: entire `.opsx/**` + entire `openspec/**` discovered
- [ ] On default: `openspec/changes` FULLY_INCLUDED when present
- [ ] `.cursor/devops/**` included on `scope=default` / `scope=process` when present
- [ ] `opsx-export/**` HARD skipped; ROOT_COVERAGE lists it SKIPPED
- [ ] ROOT_COVERAGE present for considered root folders
- [ ] On default/tmp: `.tmp/**` included when scoped; write-root is not under `.tmp`
- [ ] `include_tmp` in receipt matches whether `.tmp` was walked