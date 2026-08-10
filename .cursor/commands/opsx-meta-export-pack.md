---
component_id: opsx.commands.meta_export_pack
component_version: 0.2.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "Projectize 2026-08-07: remapped Vue/npm → poetry-python / WB Sky; opsx-lite only. 2026-08-10: EXP-01 write-root opsx-export/ + dated zip; EXP-02 default full .opsx/**+openspec/** discovery, GO optional, ROOT_COVERAGE."
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-EXPORT-PACK-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-EXPORT-PACK-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority / export roots

- Process: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`,
  `.cursor/devops/**`, … (explicit process allowlist; safety bound)
- OpenSpec tree: entire `openspec/**` present on disk (auto-discovers new
  top-level children, including `changes/**` and `changes/archive/**`)
- Project-local OPSX: entire `.opsx/**` present on disk (auto-discovers new
  top-level children, including `upstream/**` when present)
- Runtime packets: `.tmp/**` (on `scope=default` / `scope=tmp` / `scope=all_safe`)
- Export writes **only**: repo-root `opsx-export/` (separate from `.tmp`)

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not delete/move/rename **source** trees (copy-only).
- Do not expand into `src/**`, `public/**`, `backend/` app code, `.env*`,
  or secrets (process allowlist stays bounded; `.opsx/**` + `openspec/**`
  are the only whole-tree discovery roots).
- Do not copy `opsx-export/**` into the pack (write-root; nesting ban).
- Never PASS-by-absence.

### Projectization gate

Read `.opsx/projectization.yaml` before any write under `opsx-export/`.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

---

# /opsx-meta-export-pack

Side-lane **copy-only** utility: collect OPSX process surfaces + **entire**
`.opsx/**` + **entire** `openspec/**` (+ `.tmp` on default) into a new zip under
repo-root `opsx-export/` with **datetime in the archive filename**, print the
**absolute** archive path and a **ROOT_COVERAGE** report, and leave every source
tree untouched.

`GO` is **optional**. Empty invoke (no args) runs the same COPY_ONLY pack.

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

1. One command dump of **this repo’s** OPSX process + full project-local `.opsx`
   + full OpenSpec tree (including active/archived changes and **new** top-level
   folders under `.opsx/` / `openspec/` without updating a frozen subpath list)
   plus local `.tmp` runtime packets (except the export write-root).
2. Reduce ad-hoc zips under `.cursor/` (junk that must not be committed).
3. Guarantee **no delete / no move / no rename** of sources — even if the user
   types `GO`, `cleanup`, or `delete`.
4. Tell the Owner per **root folder** what was FULLY_INCLUDED vs SKIPPED.

## When to use

- Need a shareable / offline / backup snapshot of local OPSX + OpenSpec
  (+ `.tmp` packets on default scope).
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

Empty `$ARGUMENTS` is valid and runs `scope=default` COPY_ONLY (no `GO` required).

Optional tokens:

| Token | Meaning |
|---|---|
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

Unrecognized tokens that request delete/cleanup/rm → `REFUSED_DELETE_REQUEST`.

## Modes

| Input | Mode | Writes |
|---|---|---|
| empty args / any scope flags | `COPY_ONLY` | **only** new files under repo-root `opsx-export/` |
| `GO` | optional synonym | same — still COPY_ONLY; never delete |
| delete / cleanup / rm requests | refuse | **no** writes that remove anything |

There is **no** delete gate. `GO` does not authorize deletion. Empty invoke
does **not** mean read-only — it runs the pack.

## Hard boundaries (mandatory)

MUST NOT:

- delete, unlink, truncate, move, or rename any source path;
- `git clean`, `git reset --hard`, or overwrite an existing dated export zip;
- write outside repo-root `opsx-export/`;
- stage or commit the zip;
- expand into `src/`, `public/`, `backend/` application code, `.env*`,
  secrets, or IDE prefs (`.cursor/settings.json`);
- substitute for `/opsx-archive` lifecycle;
- claim verify / archive / commit readiness from this utility;
- claim `FULLY_INCLUDED` for a missing root path.

MUST:

- ensure repo-root `opsx-export/` exists (create if missing);
- write a **new** archive whose filename **must** include UTC datetime
  (`utc_ts` like `20260805-191530`): prefer `opsx-pack-<utc_ts>.zip`;
- write sibling `MANIFEST-<utc_ts>.txt` beside that zip;
- on `scope=default` / `all_safe` / `opsx` / `openspec`: **discover** actual
  top-level children under `.opsx/` and/or `openspec/` each run (new
  structures included automatically);
- copy files into zip (or optional staging under `opsx-export/` only) without
  mutating sources;
- emit Windows-style absolute path to the zip when on Windows;
- skip `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/`, and other
  obvious junk dirs when walking trees;
- HARD skip `opsx-export/**` from pack contents (write-root; nesting ban);
- emit `ROOT_COVERAGE` listing every considered root folder as
  `FULLY_INCLUDED` or `SKIPPED` with reason;
- if a requested include tree is missing → `SKIPPED (missing)` in
  ROOT_COVERAGE / EXCLUDED, continue (do not fail the whole pack unless
  **zero** include roots exist).

## Default pack contents (`scope=default`)

### Process surfaces (explicit allowlist — safety bound)

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/devops/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Skip under these trees: archives/junk already present (e.g. `commands.zip`),
`__pycache__/`, `*.pyc`, `node_modules/`. Never include `.cursor/settings.json`.

### Project-local OPSX — whole tree (auto-discover)

```text
.opsx/**
```

Enumerate **actual** top-level children of `.opsx/` each run (dirs and files).
New top-level names are included without editing this command. Includes
`.opsx/upstream/**` when present. Root files such as `manifest.yaml`,
`projectization.yaml`, `lock.yaml`, `sources.yaml` are included.

### OpenSpec — whole tree (auto-discover)

```text
openspec/**
```

Enumerate **actual** top-level children of `openspec/` each run. Includes
`openspec/changes/**` (active) and `openspec/changes/archive/**` when present,
plus any new top-level folder/file. Still skip junk patterns inside.

### Runtime packets (`.tmp`) — on `scope=default` / `scope=tmp` / `scope=all_safe`

```text
.tmp/**
```

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

### Bootstrap profile (`scope=bootstrap_profile`)

Copy **only** paths listed in `.opsx/shared/bootstrap-profile.md`
(`BOOTSTRAP_PROFILE` + do not include hard excludes). Prefer zip name
`opsx-bootstrap-profile-<utc_ts>.zip` (datetime mandatory in filename). Owner
may place the result under central `bootstrap/profile/` for
`/opsx-meta-bootstrap central=…` consumers.

Missing shared contract → `FAIL_CLOSED` `REASON: BOOTSTRAP_PROFILE_CONTRACT_MISSING`.

### Legacy include flags (no-op on full scopes)

```text
include_active_changes     → no-op when openspec tree is in scope (already included)
include_archived_changes   → no-op when openspec tree is in scope (already included)
include_upstream_snapshot  → no-op when .opsx tree is in scope (already included)
```

Never include: secrets, product app trees, `opsx-export/**`,
`openspec/changes/**/__pycache__`, binary Job artifacts under junk skips.

## ROOT_COVERAGE (mandatory)

After the pack, receipt + `MANIFEST-<utc_ts>.txt` MUST list root folders:

**Must cover at least:**

- each top-level child under `.opsx/` (when `.opsx` is in scope)
- each top-level child under `openspec/` (when `openspec` is in scope)
- each process allowlist root that was considered
- `.tmp` (when in scope)
- `opsx-export` (always listed as SKIPPED write-root)

**Statuses:**

| Status | Meaning |
|---|---|
| `FULLY_INCLUDED` | root exists and was walked into the pack (junk skip patterns only) |
| `SKIPPED` | not packed — reason required: `missing` \| `write-root nesting ban` \| `out of scope` \| `hard exclude` |

Do not invent roots that were never considered. Do not mark missing paths
`FULLY_INCLUDED`.

Example shape:

```text
ROOT_COVERAGE:
- .opsx/adapters: FULLY_INCLUDED
- .opsx/upstream: SKIPPED (missing)
- openspec/changes: FULLY_INCLUDED
- openspec/specs: FULLY_INCLUDED
- .tmp: FULLY_INCLUDED
- opsx-export: SKIPPED (write-root nesting ban)
- .cursor/agents: SKIPPED (missing)
```

## Pipeline position

```text
ENTRY_STATE: any (repo with include roots)
PREVIOUS_ALLOWED_STEP: /opsx-meta-consult route | direct invoke
COMMAND_ACTION: copy default/full trees → new dated zip under opsx-export/; emit ABSOLUTE_ARCHIVE_PATH + ROOT_COVERAGE
EXIT_STATE: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST | FAIL_CLOSED
NEXT_ALLOWED_STEP: human uses path; /opsx-meta-bootstrap central=<zip|dir> on empty peer; /opsx-meta-import-command on peer; consult/pipeline
FAILURE_OR_RECOVERY_STEP: leave partial export artifacts under opsx-export/; never delete sources; re-run (new ts)
```

## Steps

1. Projectization gate (read). If not COMPLETE → `FAIL_CLOSED`.
2. Parse `$ARGUMENTS` (may be empty). If delete/cleanup/rm intent →
   `STATUS: REFUSED_DELETE_REQUEST`, stop, no writes.
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
   (utc like `20260805-191530`).
6. Copy trees into optional staging under `opsx-export/` **or** add directly
   to zip with stable relative paths from repo root. Zip name **must** include
   datetime: `opsx-pack-<utc_ts>.zip`
   (bootstrap scope: `opsx-bootstrap-profile-<utc_ts>.zip`).
   If that exact path already exists → do not overwrite; pick a new `utc_ts`
   or `BLOCKED_IO`.
7. Write `MANIFEST-<utc_ts>.txt` beside the zip listing:
   - utc_ts, scope, include_tmp, whether discovery mode was used,
   - ROOT_COVERAGE (FULLY_INCLUDED / SKIPPED + reason),
   - skip patterns (must list `opsx-export/**`),
   - file count / approximate size if cheap.
8. Compute absolute path to `opsx-pack-<utc_ts>.zip` (Windows: full `C:\...`
   path).
9. Return output contract including ROOT_COVERAGE. Do **not** stage, commit,
   push, or delete sources.

### Implementation notes (agent)

- Prefer PowerShell/`Compress-Archive`, `zip`, or Python zipfile; bash on this
  repo is fine if paths are correct and sources untouched.
- Never `rm -rf` staging of **sources**. Optional staging under `opsx-export/`
  may be left as-is after zip; do not delete source trees to “clean up”.
- Cleaning optional staging after zip is **optional** and only allowed
  **inside** repo-root `opsx-export/` for artifacts created this run —
  never outside it; never delete prior dated packs. Prefer leaving zip +
  manifest both present if unsure.
- When walking any tree, do not follow/copy into `opsx-export/**`.
- Discovery: `Path('.opsx').iterdir()` / `Path('openspec').iterdir()` — do not
  require a frozen subpath list for those two roots.
- Time-budget large `.tmp` / large `openspec/changes/archive` /
  `.opsx/upstream` walks; on hang → `BLOCKED_IO`.

## Output contract

```text
STATUS: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST | FAIL_CLOSED
MODE: COPY_ONLY
COMMAND: /opsx-meta-export-pack

EXPORT_PACK_RECEIPT:
- utc_ts:
- scope:
- include_tmp: true|false
- discovery_opsx: true|false
- discovery_openspec: true|false
- absolute_archive_path:
- manifest_path:
- ROOT_COVERAGE:
  - <root>: FULLY_INCLUDED | SKIPPED (<reason>)
- excluded_or_skipped: [notes; must mention opsx-export/** nesting ban]
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
| No include roots exist | `BLOCKED_NEEDS_INPUT` | confirm cwd / repo |
| I/O / zip failure | `BLOCKED_IO` | report path attempted; leave partial; re-run |
| User asked delete | `REFUSED_DELETE_REQUEST` | explain ban; offer re-run copy-only |
| Ambiguous scope | `BLOCKED_NEEDS_INPUT` | ask one scope question |

## Authority

- Owns: copy-only export pack contents via discovery + process allowlist +
  absolute path receipt + ROOT_COVERAGE.
- Does **not** own: change archive, doctor deletes, process commits, verify, inbound merge.
- Companion: `/opsx-meta-commit` must keep export zips OUT_OF_SCOPE.
- Peer: `/opsx-meta-import-command` consumes packs produced here (or equivalents).

## Anti-patterns

- Naming or describing this as “archive the change”
- Deleting old `opsx-export/*` “to save space” from this command
- Nesting prior `opsx-export/**` contents into a new pack
- Writing under `.tmp/opsx-export/` again (legacy; write-root is repo-root
  `opsx-export/`)
- Using a zip name without datetime (e.g. bare `opsx-pack.zip`)
- Dumping whole monorepo / `src/` / `public/`
- Committing dated packs into `.cursor/` or `opsx-export/` via process commit
- Using `GO` to unlock delete
- Requiring `GO` before a default pack will run
- Omitting `openspec/changes/**` or new `.opsx`/`openspec` top-level children
  from default while claiming a full dump
- Omitting ROOT_COVERAGE or marking missing roots FULLY_INCLUDED
- Expanding discovery beyond `.opsx/**` + `openspec/**` into product trees

## Self-review checklist

Before returning:

- [ ] `delete_performed: false`
- [ ] Empty invoke or `GO` both run COPY_ONLY (GO optional)
- [ ] Writes only under repo-root `opsx-export/`
- [ ] Archive filename includes `utc_ts` (`opsx-pack-<utc_ts>.zip` or
      bootstrap dated equivalent)
- [ ] `absolute_archive_path` is absolute and clickable/copyable
- [ ] Not confused with `/opsx-archive` or `/opsx-meta-import-command`
- [ ] Not expanded into product/secrets / `.cursor/settings.json`
- [ ] On default: entire `.opsx/**` + entire `openspec/**` discovered
- [ ] On default: `openspec/changes` FULLY_INCLUDED when present
- [ ] `.cursor/devops/**` included on `scope=default` / `scope=process` when present
- [ ] `opsx-export/**` HARD skipped; ROOT_COVERAGE lists it SKIPPED
- [ ] ROOT_COVERAGE present for considered root folders
- [ ] On default/tmp: `.tmp/**` included when scoped; write-root is not under `.tmp`
- [ ] `include_tmp` in receipt matches whether `.tmp` was walked
