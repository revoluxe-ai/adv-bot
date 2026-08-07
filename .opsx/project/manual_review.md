# Manual review — scripts projectization

Generated: 2026-08-07T06:02:24Z  
Command: `/opsx-projectize:GO`  
Target: `meta-repo/scripts` (`repo_family_id: scripts`)  
Bootstrap seed: `.tmp/opsx-bootstrap/20260807T055730Z/MERGE_RECEIPT.md`  
Central: `C:\Users\vkita\my_code\opsx-central` (`sources/game/go-to-prod` bytes)

## Owner decisions applied

1. Scripts-native projectize (not Vue/npm game wipe).
2. **KEEP** product OpenSpec (`changes/`, `decisions/`, `specs/`, `config.yaml`).
3. **KEEP** `app/**`; no Poetry/npm installs; no commit.
4. Hub commands retargeted: `opsx-projectize`, `opsx`, `opsx-meta` →
   `OPSX-SCRIPTS-*` + adapters `opsx-lite` + `poetry-scripts`.

## Checks (must pass for COMPLETE)

| Check | Result |
|---|---|
| `.opsx/adapters/poetry-scripts/README.md` present | PASS |
| `openspec/config.yaml` unchanged by this GO | PASS (KEEP) |
| Product `openspec/changes` not deleted | PASS |
| `opsx-projectize.md` no longer Vue wipe default | PASS |
| Activation + provenance registries written | PASS |
| `pyproject.toml` / `app/` present | PASS |

## Activation summary

- CORE + DEFAULT_INSTALL commands: `ACTIVE` (bootstrap + local product set).
- Other local `.cursor/commands/opsx*.md`: `ACTIVE` (pre-existing scripts surface).
- Registry: `.opsx/registry/command_activation.ndjson`, `provenance.ndjson`.

## Deferred / follow-ups

| Item | Priority | Next |
|---|---|---|
| Remaining game wording inside older admin/bug commands | MEDIUM | `/opsx-meta-fix-command-defects` or targeted import |
| Snapshot publish for `scripts` family | LOW | `/opsx-meta-update-snapshot` when ready |
| Extra catalog commands | LOW | `/opsx-meta-import-command` |
| Adapter depth (exact Poetry script matrix) | LOW | `/opsx-adapt-project` |

## Forbidden regressions

- Do not re-run game-shaped projectize that deletes OpenSpec/product trees.
- Second `/opsx-projectize:GO` without Owner reset → fail-closed.
