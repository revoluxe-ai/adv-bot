---
description: "Copy-only portable zip of all OPSX process + OpenSpec trees; emit absolute path. Always-all; no scope flags."
argument-hint: "[GO]"
---

# /opsx-admin-command-export-bundle

Exclusive owner of **portable OPSX export**: copy-only zip of fixed directory
roots (always all), then print absolute path + `file://` URI for transfer to
another repo.

This command does **not** commit, archive a product change, delete sources, or
rewrite process trees.

**Packer SoT (deterministic):** `.cursor/opsx-export/export_bundle.py`

## Purpose

Перенос OPSX из проекта в другое место одним zip:

- пакует **целые деревья** (новые файлы внутри подхватываются сами);
- **всегда all** — параметра `scope=` нет и не будет;
- source trees не изменяет и не удаляет;
- пишет только новый zip под `opsx-export/`.

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| (absent) | `DRY_RUN` — inventory only, no zip |
| exact `GO` | write zip + print absolute path |

Unknown tokens → `STATUS: BLOCKED` (do not invent scope flags).

## Always-all include roots (fixed)

Directory walk (every present root):

```text
.cursor/
openspec/
.agents/
.github/prompts/
.github/skills/
```

Single files if present:

```text
AGENTS.md
.github/copilot-instructions.md
.github/git-commit-instructions.md
```

Excludes (only these; not a file allow-list):

- `.cursor/settings.json` (IDE prefs)
- `*.zip`, `*.pyc`, `__pycache__/`, `.git/`, `node_modules/`, `.venv/`
- Cursor `projects/` under `.cursor` if present

Zip member paths preserve repo-relative structure (e.g. `openspec/config.yaml`).

## When to use

- Перенос OPSX в другой репозиторий
- Snapshot process + OpenSpec surfaces before machine / repo move

## When not to use

- Local commit of process files → `/opsx-admin-command-commit`
- Product OpenSpec change archive → `/opsx-archive`
- Day-to-day navigate → `/opsx-pipeline`
- Design new command → `/opsx-admin-command-design-command`

## Authority boundary

- Owns only the export zip artifact under `opsx-export/`
- Does **not** stage/commit/push
- Does **not** mutate include roots
- Does **not** bypass verify / apply / archive product gates
- Zip is junk for `/opsx-admin-command-commit` (never commit the artifact)

## Modes

| Input | Mode | Writes |
|-------|------|--------|
| no `GO` | `DRY_RUN` | none |
| `GO` | `EXPORT` | one new zip file only |

## Steps

1. Resolve repo root (directory that contains `.cursor/` and/or `openspec/`).
2. Run the packer (preferred; do not re-implement ad-hoc zip logic):

   ```bash
   # dry-run
   poetry run python .cursor/opsx-export/export_bundle.py --dry-run

   # write zip
   poetry run python .cursor/opsx-export/export_bundle.py
   ```

   Fallback if Poetry unavailable:

   ```bash
   python .cursor/opsx-export/export_bundle.py
   ```

3. Never pass invented `--scope` flags (script has none).
4. On success with `GO`, report absolute path and `file://` URI from script stdout.
5. Do not delete prior zips unless the owner explicitly asks in a later invoke.

## Output contract

### No `GO`

```text
STATUS: DRY_RUN_READY
MODE: DRY_RUN
REPO_ROOT: <abs>
FILE_COUNT: <n>
BYTES: <n>
INCLUDE_DIR_ROOTS: …
WHAT_HAPPENED: inventoried always-all OPSX roots; no zip written
WHY: GO absent
CURRENT_STATE: dry_run_ready
OWNER_DECISION_REQUIRED: yes — run with GO to write zip
NEXT_ACTION: /opsx-admin-command-export-bundle GO
DO_NOT_DO_YET: commit the zip; invent scope=; mutate source trees
```

### With `GO`

```text
STATUS: EXPORTED
MODE: EXPORT
REPO_ROOT: <abs>
FILE_COUNT: <n>
BYTES: <n>
ZIP_ABS_PATH: <absolute filesystem path>
FILE_URI: file:///...
ZIP_BYTES: <n>
WHAT_HAPPENED: copy-only zip written under opsx-export/
WHY: GO present; always-all roots packed
CURRENT_STATE: exported
OWNER_DECISION_REQUIRED: none (copy ZIP_ABS_PATH to target)
NEXT_ACTION: /opsx-admin-command-commit   # only if this command/helper was just added/edited
DO_NOT_DO_YET: commit the zip artifact; delete source trees; push
```

### Failure

```text
STATUS: BLOCKED | DATA_GAP
REASON: …
NEXT_ACTION: fix path / poetry / disk; retry
```

## Reliability invariant

Include roots are **directories**, not a language/command file list. Refactors
that add/rename/move files *inside* those trees are packed automatically.
Only a new top-level OPSX root outside the fixed list requires a command +
script root-list update (same coherent packet).

## Absolute prohibitions

- No `scope=` / partial packs
- No delete/modify of include roots
- No `git add` / commit / push of the zip
- No product `app/` / `tests/` packing
- No secrets harvest beyond what already lives in include roots (still exclude
  `.env` if somehow nested — treat as exclude if encountered)

## Self-review

- [ ] Packer script used (not ad-hoc divergent zip)
- [ ] Always-all; no scope flag honored
- [ ] Sources unchanged
- [ ] `ZIP_ABS_PATH` + `FILE_URI` printed on EXPORT
- [ ] NEXT_ACTION for process commit points to `/opsx-admin-command-commit`
