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
- [ ] `.opsx` adapters/registry included on `scope=default` when present
