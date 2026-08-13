# Manual review — projectize COMPLETE (restore)

Generated: 20260812T235831Z
Source: `/opsx-projectize:GO`
Mode: restore mid-rebase (lock yaml absent from WT; tip already COMPLETE)

## Target

- Product: WB Sky (`adv-bot` Poetry package)
- Adapters: `opsx-lite` + `poetry-python`
- Not a Vue/npm game tree

## Applied

- Restored `.opsx/projectization.yaml`, `sources.yaml`, `manifest.yaml`, `lock.yaml` from branch tip `implement-resolve-conflict-command` @ `(19e4d939f)`
- Did **not** wipe product `openspec/**`
- Did **not** seed `vue-npm`
- Did **not** modify active rebase UU paths (`opsx-devops`, `opsx-admin-command-commit`, devops state)
- Left `opsx-resolve-conflict` to rebase todo / later import

## Preserved

- Full product `openspec/**`
- Existing `.opsx/adapters/poetry-python/**`, shared contracts, activation registry
- Gate/meta command files already on disk

## Deferred / Owner follow-up

- Finish interactive rebase UU → `git rebase --continue`
- `opsx-resolve-conflict` arrives in later rebase picks (or import if still ABSENT)
- Optional: `/opsx-meta-commit` for restored yaml if tip files differ from committed tip after rebase

## Checks before COMPLETE

- [x] `openspec/` file count unchanged by this APPLY
- [x] Gate commands present
- [x] `poetry-python` present; `vue-npm` absent
- [x] Lock set to COMPLETE with `normal_commands_enabled: true`
- [x] `sources.yaml` without machine-absolute `central_root` (tip version)
