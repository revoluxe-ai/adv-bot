---
name: /opsx-admin-command-export-pack
id: opsx-admin-command-export-pack
category: Workflow
description: "Copy-only OPSX/OpenSpec process pack into .tmp zip; print absolute path; never delete sources"
argument-hint: "[scope=default|process|openspec|all_safe] [include_active_changes] [include_archived_changes]"
---

# /opsx-admin-command-export-pack

Side-lane **copy-only** utility: collect allowlisted OPSX / OpenSpec surfaces into
a new zip under `.tmp/opsx-export/<utc_ts>/`, print the **absolute** archive path,
and leave every source tree untouched.

This is **not** `/opsx-archive` (lifecycle move/promote of a completed change).
This is **not** `/opsx-doctor` (may delete leftovers).
This is **not** a commit path (export artifacts stay out of git).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including Read / tool I/O budgets).

## Purpose

1. Give the human one portable pack of OPSX-related process + OpenSpec SoT.
2. Reduce ad-hoc zips under `.cursor/` (junk that must not be committed).
3. Guarantee **no delete / no move / no rename** of sources — even if the user
   types `GO`, `cleanup`, or `delete`.

## When to use

- Need a shareable / offline / backup snapshot of OPSX commands + specs.
- Preparing an external review of process surfaces without cloning the monorepo.
- After consult routes «нужен dump OPSX» here.

## When not to use

- Archive a completed OpenSpec change → `/opsx-archive`
- Commit process surfaces → `/opsx-admin-command-commit`
- Delete corrupt leftover changes → `/opsx-doctor`
- Client/CS product brief → `/opsx-distribute-brief`
- Day-to-day navigate → `/opsx-pipeline`
- Product code / app dump → out of scope (refuse)

## User input

```text
$ARGUMENTS
```

Optional tokens:

| Token | Meaning |
|---|---|
| `scope=default` | process surfaces + openspec static SoT (default) |
| `scope=process` | process surfaces only |
| `scope=openspec` | openspec static SoT only |
| `scope=all_safe` | same as default (alias; still bounded) |
| `include_active_changes` | also copy `openspec/changes/*` active roots (not archive/) |
| `include_archived_changes` | also copy `openspec/changes/archive/**` (can be large) |

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
- expand allowlist into `app/`, `tests/`, `.env*`, secrets, Job outputs under
  `.tmp/opsx-scripts/**`, or IDE prefs (`.cursor/settings.json`);
- substitute for `/opsx-archive` lifecycle;
- claim verify / archive / commit readiness from this utility.

MUST:

- create a **new** timestamped directory every run;
- copy files into that directory (or stream into zip) without mutating sources;
- emit Windows-style absolute path to the zip when on Windows;
- skip `__pycache__/`, `*.pyc`, `.pytest_cache/`, and other obvious junk dirs
  when walking trees;
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
`__pycache__/`, `*.pyc`.

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

### Optional (off by default)

```text
include_active_changes     → openspec/changes/<active>/  (not archive/)
include_archived_changes   → openspec/changes/archive/**
```

Never include: `openspec/changes/**/__pycache__`, binary Job artifacts, secrets.

## Pipeline position

```text
ENTRY_STATE: any (repo with allowlisted trees)
PREVIOUS_ALLOWED_STEP: /opsx-admin-command-consult route | direct invoke
COMMAND_ACTION: copy allowlisted paths → new zip; emit ABSOLUTE_ARCHIVE_PATH
EXIT_STATE: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST
NEXT_ALLOWED_STEP: human uses path; consult/pipeline as needed
FAILURE_OR_RECOVERY_STEP: leave partial export dir; never delete; re-run (new ts)
```

## Steps

1. Parse `$ARGUMENTS`. If delete/cleanup/rm intent →
   `STATUS: REFUSED_DELETE_REQUEST`, stop, no writes.
2. Resolve `scope` (default=`default`) and optional include flags.
3. Build include-root list from allowlist; verify at least one root exists.
4. Create `.tmp/opsx-export/<utc_ts>/` (utc like `20260805-191530`).
5. Copy allowlisted trees into a staging folder **or** add directly to zip
   with stable relative paths from repo root. Prefer zip name:
   `opsx-pack.zip`.
6. Write `MANIFEST.txt` beside the zip listing:
   - utc_ts, scope, include flags, root paths included, skip patterns,
   - file count / approximate size if cheap.
7. Compute absolute path to `opsx-pack.zip` (Windows: full `C:\...` path).
8. Return output contract. Do **not** stage, commit, push, or delete anything.

### Implementation notes (agent)

- Prefer PowerShell/`Compress-Archive` or Python zipfile; on this repo shell may
  be bash — either is fine if paths are correct and sources untouched.
- Never `rm -rf` staging of **sources**. Staging under the new export dir may
  be left as-is after zip; do not delete source trees to “clean up”.
- Cleaning the export staging folder after zip is **optional** and only allowed
  **inside** the new `.tmp/opsx-export/<utc_ts>/` directory created this run —
  never outside it. Prefer leaving staging + zip both present if unsure.
- Time-budget large `include_archived_changes` walks; on hang → `BLOCKED_IO`.

## Output contract

```text
STATUS: EXPORT_PACK_READY | BLOCKED_NEEDS_INPUT | BLOCKED_IO | REFUSED_DELETE_REQUEST
MODE: COPY_ONLY
COMMAND: /opsx-admin-command-export-pack

EXPORT_PACK_RECEIPT:
- utc_ts:
- scope:
- include_active_changes: true|false
- include_archived_changes: true|false
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
- do not commit the zip (/opsx-admin-command-commit will refuse)
- do not treat this as /opsx-archive
- do not ask this command to delete anything
```

`NEXT_ACTION` after success is usually `none` (pack is ready) or
`/opsx-admin-command-commit` **only** if process command files were edited in
the same chat for other reasons — never to commit the zip.

## Failure / recovery

| Condition | STATUS | NEXT |
|---|---|---|
| No allowlisted roots exist | `BLOCKED_NEEDS_INPUT` | confirm cwd / repo |
| I/O / zip failure | `BLOCKED_IO` | report path attempted; leave partial; re-run |
| User asked delete | `REFUSED_DELETE_REQUEST` | explain ban; offer re-run copy-only |
| Ambiguous scope | `BLOCKED_NEEDS_INPUT` | ask one scope question |

## Authority

- Owns: copy-only export pack contents via allowlist + absolute path receipt.
- Does **not** own: change archive, doctor deletes, process commits, verify.
- Companion: `/opsx-admin-command-commit` must keep export zips OUT_OF_SCOPE.

## Anti-patterns

- Naming or describing this as “archive the change”
- Deleting old `.tmp/opsx-export/*` “to save space” from this command
- Dumping whole monorepo / `app/`
- Committing `opsx-pack.zip` into `.cursor/`
- Using `GO` to unlock delete

## Self-review checklist

Before returning:

- [ ] `delete_performed: false`
- [ ] Writes only under this run’s `.tmp/opsx-export/<utc_ts>/`
- [ ] `absolute_archive_path` is absolute and clickable/copyable
- [ ] Not confused with `/opsx-archive`
- [ ] Allowlist not expanded into product/secrets
