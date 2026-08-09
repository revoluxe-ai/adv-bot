# Manual review — projectize COMPLETE

Generated: 20260807T181322Z
Source: `/opsx-projectize:GO`
Central bind: `C:/Users/vkita/my_code/opsx-central` (from `.opsx/sources.yaml`)
Bootstrap evidence: `.tmp/opsx-bootstrap/20260807T172840Z/MERGE_RECEIPT.md`

## Target

- Product: WB Sky (`adv-bot` Poetry package)
- Adapters: `opsx-lite` + `poetry-python`
- Not a Vue/npm game tree — game donor wipe plan was rejected

## Applied

- Rewrote `/opsx-projectize` and `/opsx-adapt-project` for Poetry/WB
- Dropped `vue-npm` from seeded meta `required_adapters`
- Remapped game contract ids on meta surfaces → `OPSX-WB-*`
- Seeded `.opsx/adapters/poetry-python/README.md`
- Rebuilt activation (DEFAULT/CORE 27) + provenance event
- Deleted typo file `.cursor/opsx-meta-bootstram` (if present)

## Preserved (must stay)

- Full product `openspec/**` (changes, archive, specs, decisions, `config.yaml`)
- Product lifecycle command bodies that already won locally
- `.cursor/rules/**`, `.cursor/pipeline/**`

## Deferred

- Registering ~33 extra on-disk commands not in DEFAULT activation
  (bug-hunt, admin-command*, test*, …) — use `/opsx-meta-import-command`
  or a later adapt pass if Owner wants them activated
- Spec Kit (`.specify/`) remains deferred
- `repo_family_id` in sources/lock still `unknown` until snapshot/index

## Checks before COMPLETE

- [x] `openspec/` file count unchanged by this APPLY
- [x] Gate commands present under `.cursor/commands/`
- [x] `poetry-python` adapter README present
- [x] `vue-npm` adapter absent
- [x] Lock set to COMPLETE with `normal_commands_enabled: true`
