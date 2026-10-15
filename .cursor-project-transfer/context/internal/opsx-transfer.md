# OPSX: перенос process-surface между репозиториями / ветками

**Источник обзора (read-only):** worktree  
`C:\Users\vkita\my_code\meta-repo\adv-bot-full-command-transfer`, ветка  
`feature/opsx-full-command-transfer`.  
В основном `adv-bot` на `stage` отдельного указателя на этот процесс не найдено.

## Что переносится («knowledge»)

Не продуктовый код (`app/**`, `openspec/changes/**` как дамп, секреты).  
**Process surface OPSX / OpenSpec для агентов:**

- `.cursor/commands/**`, rules, skills, pipeline, static-check, antipattern-gate, …
- статические части `openspec/` (config, policies, schemas, specs, decisions — по allowlist)
- `.opsx/**` (adapters, registry, shared, project, manifest, projectization)
- `AGENTS.md`, `.agents/**`, зеркала `.github/skills|prompts`

SoT allowlist: `.opsx/sources.yaml`. Экспорт — copy-only, без удаления источника.

## Откуда → куда (full command transfer на этой ветке)

| Роль | Путь / идентификатор |
|------|----------------------|
| **Donor (SOURCE)** | `C:\Users\vkita\my_code\game`, commit `91311ada29721cfb9aab7a00e1dc4d2a0a8d1982` |
| **TARGET** | `adv-bot-full-command-transfer`, baseline `1a75e9a04363753cb281530db4f75f8e409492f3` |
| **Объём** | ровно **100** top-level `*.md` в `.cursor/commands/` у donor |

Ledger: `.opsx/registry/command_transfer_manifest.md`  
Итоговый статус: `.opsx/registry/command_transfer_completion.json`  
(`TRANSFER_SURFACE_MATERIALIZED_WITH_BOUNDED_HOLDS`, 100 команд, коллизии same-name).

Состояния по команде: `EXISTING_ADAPTATION_REQUIRED` (сохранить WB/poetry-реализацию),  
`IMPLEMENTED_UNVERIFIED`, `FUNCTIONAL_PROVEN`, `SOURCE_STAGED_MIGRATION_HOLD`.

## Типовой процесс (не только game→adv-bot)

1. **Пустой / чужой репо:** `/opsx-meta-bootstrap` (шаги bind → meta → lifecycle → support), затем `/opsx-projectize` → lock `COMPLETE` в `.opsx/projectization.yaml`.
2. **Точечный импорт команд:** `/opsx-meta-import-command` (`OPSX-WB-META-IMPORT-01`) — каталог central или raw donor; staging `.opsx/runs/inbound/<UTC>/`; не класть архивы в `.opsx/import/` (там только lineage-доки).
3. **Пакетный перенос zip:** `/opsx-meta-export-pack` или `/opsx-admin-command-export-bundle` — zip под `opsx-export/`, пути для копирования в другой репо.
4. **Адаптация под WB Sky / Poetry:** `/opsx-projectize` после bootstrap/import; vue-npm у donor не считается primary (см. manifest, adapters).

Связанные meta-команды (имена): `opsx-meta-export-pack`, `opsx-meta-import-command`,  
`opsx-meta-bootstrap`, `opsx-projectize`, `opsx-admin-command-export-bundle`,  
`opsx-meta-discover`, `opsx-meta-fix-command-defects`, `opsx-learn-from-bug` /  
`opsx-admin-command-promote-process-lesson` (переносимые *process lessons*, не каталог команд).

## Bootstrap lineage (ранний donor, не game)

`.opsx/import/README.md`: snapshot из `opsx-central` / unknown branch  
`pause-on-empty-keuywords-and-free-on-it`; product/openspec donor **не** копировался в дерево.

## Верификация transfer-ветки (поверхностно)

`command_transfer_completion.json`: pytest transfer-контракты, bounded-verify,  
обязательства по live-run для `IMPLEMENTED_UNVERIFIED`; Temporal SDK activation отдельным блоком.

---

*Обзор только по README/manifest/commands/registry; полное дерево не сканировалось.*
