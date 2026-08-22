# Manual review — projectize COMPLETE

Generated: 20260812T214500Z (initial GO)
Updated: 20260822T182013Z (lock recovery GO)
Source: `/opsx-projectize:GO` (recovery)
Central bind: `C:/Users/vkita/my_code/opsx-central` (from `.opsx/sources.yaml`)
Bootstrap evidence (historical):
- `.tmp/opsx-bootstrap/20260812T212332Z/MERGE_RECEIPT.md` (STEP 1)
- `.tmp/opsx-bootstrap/20260812T212617Z/MERGE_RECEIPT.md` (STEP 2)
- `.tmp/opsx-bootstrap/20260812T214056Z/MERGE_RECEIPT.md` (STEP 3)

## Target

- Product: WB Sky (`implement-free-bot-rebase` / adv-bot Poetry package)
- Adapters: `opsx-lite` + `poetry-python`
- Not a Vue/npm game tree — game donor wipe plan rejected

## Applied (initial GO 20260812)

- Seeded `.opsx/adapters/{README,poetry-python/README}.md`
- Seeded support: `.opsx/shared/{lifecycle,evidence-contract}.md`,
  `.opsx/import/README.md`
- Rebuilt activation (DEFAULT/CORE 27) + provenance `projectize_complete`
- Updated `.opsx/manifest.yaml` for WB/poetry COMPLETE
- Wrote this manual review

## Applied (lock recovery GO 20260822)

- Restored `.opsx/projectization.yaml`, `manifest.yaml`, `lock.yaml`,
  `sources.yaml` (gate files were missing; surfaces intact)
- Seeded `.opsx/project/quality-gates.md` (poetry-python gates)
- Rewrote vue-npm residue in meta-surface commands:
  `opsx-meta-consult`, `opsx-meta-commit`, `opsx-meta-fix-command-defects`,
  `opsx-meta-design-command`
- Appended provenance `projectize_lock_restored`
- Activation registry unchanged (32 rows; imports preserved)

## Preserved (must stay)

- Full product `openspec/**` (changes, archive, specs, decisions, `config.yaml`)
- Existing product lifecycle command bodies already on disk
- `.cursor/rules/**`, `.cursor/pipeline/**`
- Bootstrap-seeded WB-remapped meta commands (no vue-npm required_adapters)

## Deferred

- Extra on-disk commands not in DEFAULT activation
  (bug-hunt, admin-command*, test*, …) — use `/opsx-meta-import-command`
  or a later adapt pass if Owner wants them activated
- Spec Kit (`.specify/`) remains deferred
- `repo_family_id` in lock still `implement-free-bot-rebase` until
  `/opsx-meta-update-snapshot` publishes adv-bot family binding
- `.opsx/upstream/**` absent — meta-consult upstream snapshot optional

## Checks before COMPLETE

- [x] `openspec/` product tree preserved (no wipe)
- [x] Gate commands present under `.cursor/commands/`
- [x] `poetry-python` adapter README present
- [x] `vue-npm` adapter absent
- [x] Lock set to COMPLETE with `normal_commands_enabled: true`
- [x] `quality-gates.md` present; meta commands cite poetry-python gates
