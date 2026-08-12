# Manual review — projectize COMPLETE

Generated: 20260812T214200Z
Source: `/opsx-projectize:GO`
Central bind: `C:/Users/vkita/my_code/opsx-central` (from `.opsx/sources.yaml`)
Bootstrap evidence: `.tmp/opsx-bootstrap/20260812T212300Z/MERGE_RECEIPT.md`
Prior projectize: 20260807T181322Z (WB/poetry already applied; this run re-locks after bind reseed)

## Target

- Product: WB Sky (`adv-bot` Poetry package)
- Adapters: `opsx-lite` + `poetry-python`
- Not a Vue/npm game tree — `vue-npm` not seeded

## Applied (this :GO)

- Rewrote `.opsx/projectization.yaml` → `COMPLETE` + `normal_commands_enabled: true`
- Rewrote `.opsx/manifest.yaml` to WB COMPLETE record
- Appended `projectize_complete` provenance
- Left activation registry rows intact (DEFAULT/CORE + prior imports)
- Did **not** touch `openspec/**`, `app/**`, `tests/**`, `pyproject.toml`

## Preserved (must stay)

- Full product `openspec/**` (changes, archive, specs, decisions, policies, evolution)
- Product lifecycle + meta command bodies already on disk
- `.cursor/rules/**`, `.cursor/pipeline/**`
- Absolute `central_root` in `.opsx/sources.yaml`

## Deferred

- Extra on-disk commands not in DEFAULT activation (bug-*, admin-*, test*, …)
  → `/opsx-meta-import-command` if Owner wants activation
- Spec Kit (`.specify/`)
- `repo_family_id` still `unknown` until snapshot/index
- `openspec/config.yaml` missing — **not** regenerated from game template
- Optional remap of `opsx-meta-bootstrap` `OPSX-GAME-*` contract id

## Checks before COMPLETE

- [x] `openspec/` product tree not modified by this APPLY
- [x] Gate commands present under `.cursor/commands/`
- [x] `poetry-python` adapter README present
- [x] `vue-npm` adapter absent
- [x] Lock set to COMPLETE with `normal_commands_enabled: true`
