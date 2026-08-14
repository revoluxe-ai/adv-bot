# Manual review — projectize COMPLETE (merge-resolved)

Generated: 20260812T235831Z
Source: `/opsx-projectize:GO` then merge of PR #432 (`implement-resolve-conflict-command`) into `distribute-command`
Prior projectize: 20260812T214200Z (bind reseed / COMPLETE rewrite; Bootstrap evidence `.tmp/opsx-bootstrap/20260812T212300Z/MERGE_RECEIPT.md`)
Earlier baseline: 20260807T181322Z (WB/poetry already applied)

## Target

- Product: WB Sky (`adv-bot` Poetry package)
- Adapters: `opsx-lite` + `poetry-python`
- Not a Vue/npm game tree — `vue-npm` not seeded

## Applied (this lineage)

- Rewrote `.opsx/projectization.yaml` → `COMPLETE` + `normal_commands_enabled: true`
- Rewrote `.opsx/manifest.yaml` to WB COMPLETE record
- Appended `projectize_complete` provenance
- Restored / aligned `.opsx/projectization.yaml`, `sources.yaml`, `manifest.yaml`, `lock.yaml` with COMPLETE tip state
- This merge landed `.cursor/opsx-resolve-conflict/**` and `.cursor/commands/opsx-resolve-conflict.md`
- Left activation registry rows intact (DEFAULT/CORE + prior imports)
- Did **not** wipe product `openspec/**`
- Did **not** touch `app/**`, `tests/**`, `pyproject.toml`
- Did **not** seed `vue-npm`

## Preserved

- Full product `openspec/**` (changes, archive, specs, decisions, policies, evolution)
- Product lifecycle + meta / gate command bodies already on disk
- `.cursor/rules/**`, `.cursor/pipeline/**`
- Existing `.opsx/adapters/poetry-python/**`, shared contracts, activation registry

## Deferred / Owner follow-up

- Extra on-disk commands not in DEFAULT activation (bug-*, admin-*, test*, …)
  → `/opsx-meta-import-command` if Owner wants activation
- Spec Kit (`.specify/`)
- `repo_family_id` / snapshot index still pending until `/opsx-meta-update-snapshot`
- `openspec/config.yaml` missing — **not** regenerated from game template
- Optional remap of `opsx-meta-bootstrap` `OPSX-GAME-*` contract id
- Optional: `/opsx-meta-commit` for any remaining non-conflict process dirt after merge

## Checks before COMPLETE

- [x] `openspec/` product tree not modified by projectize APPLY
- [x] Gate commands present under `.cursor/commands/`
- [x] `poetry-python` adapter present; `vue-npm` absent
- [x] Lock set to COMPLETE with `normal_commands_enabled: true`
- [x] `sources.yaml` without machine-absolute `central_root` (portable tip version)
