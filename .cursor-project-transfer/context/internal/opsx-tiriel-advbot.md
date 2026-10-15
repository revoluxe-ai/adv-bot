---
cursor:
  subagentId: "bc-b06d37e0-341a-536d-88db-abf7a6139278"
---

# OPSX: ориентация для tiriel-game и adv-bot

## Что такое OPSX в этих репозиториях

**OPSX** — это не отдельный рантайм-сервис, а **договорённый процесс работы агента в Cursor**: набор slash-команд (`/opsx-*`), общих контрактов в `.opsx/`, правил в `.cursor/rules/` и (для продуктовых задач) **OpenSpec** в `openspec/changes/**`. Агент читает тело команды как контракт: что можно писать, какие гейты, какой `NEXT_ACTION`.

Две **дорожки (lanes)**:

| Дорожка | Вход | Смысл |
|--------|------|--------|
| **PRODUCT** | `/opsx`, `/opsx-pipeline` | Жизненный цикл фичи/бага: планирование → код → проверки → архив → коммит продукта |
| **META / COMMAND** | `/opsx-meta`, `/opsx-meta-*` | Процесс-плоскость: bootstrap, импорт команд, снапшоты в central, фиксы контрактов, коммит process-surfaces |

Пока нет `.opsx/` или `projectization.yaml` со `status: COMPLETE`, обычные команды **закрыты** (`FAIL_CLOSED`) → `/opsx-meta-bootstrap` или `/opsx-projectize`.

## Как устроен «запуск» и команда

1. **Ориентация (read-only):** `/opsx` выбирает lane и даёт один советуемый шаг; `/opsx-meta` — то же для command-plane. SoT: `.opsx/shared/meta-orientation.md`.
2. **Продуктовый spine** (`.opsx/shared/lifecycle.md`):  
   `explore` → `new|ff|update` → `continue` → `apply` → план верификации → bounded executors → `verify` → `archive` → `commit` (часто с явным **GO** на опасных шагах).
3. **Навигация:** `/opsx-pipeline` опирается на `.cursor/pipeline/GRAPH.md` (инвентарь ~72 команд в tiriel) — **совет**, не принудительный путь; контракт конкретной команды важнее.
4. **Форма команды:** файл `.cursor/commands/opsx-<name>.md` с YAML-frontmatter (`contract_id`, `runtime_class`, `required_adapters`, иногда `upstream_snapshot`). В **tiriel** многие команды обёрнуты в **TARGET OVERRIDE** (адаптер `vue-npm`: вместо Poetry/pytest — `npm run build` и явные `UNAVAILABLE`). В **adv-bot** — адаптер `opsx-lite` + `poetry-python` (pytest, pyright-strict, devops через `/opsx-devops`).
5. **Один активный slash на ход** (правило `opsx-single-active-command`): второй `/opsx-*` в том же сообщении — только текст, не вызов.
6. **Артефакты прогона:** продукт — `openspec/changes/<id>/`; процесс-импорт — staging `.opsx/runs/inbound/**`; долгие миссии — `.opsx/runs/**` (bug-cases, orch-missions и т.д.) — для ориентации достаточно знать, что это **журнал/доказательства**, не код приложения.

## Репозитории на этой VM

| | **tiriel-game** («Kirill Game») | **adv-bot** (WB Sky) |
|---|----------------|----------------------|
| Имя в npm | `tiriel` (`package.json`) | Python/Poetry, `target_model: wb-sky-poetry-python` |
| Ветка (контекст VM) | см. checkout (Owner-ветка в AGENTS.md) | `stage` |
| Контракт OPSX | `OPSX-GAME-EXECUTION-01` | `OPSX-WB-PROJECTIZE-01` |
| Команд `opsx*.md` | ~96 | ~70 |
| Замороженный upstream | **есть:** `.opsx/upstream/a71601dba3b9/` (read-only эталон) | **нет** каталога upstream на диске; ссылки в meta-командах на те же пути как на snapshot-имена |
| Расширения | Temporal (`tools/temporal/`), bounded verification, browser-check handoff, `mental-contracts/`, богаче bug/orch-набор | DevOps-команда, antipattern-gate, pyright/external-call coverage; меньше shared-файлов в `.opsx/shared/` |

**tiriel впереди adv-bot** в смысле **зрелости OPSX-плоскости**: полный набор meta-команд (design/fix/import/snapshot/index/discover), frozen upstream + full-body correction, расширенный pipeline graph, отдельный слой верификации (Tempo + ledger), больше общих контрактов (`bounded-executor`, `execution-preflight`, `static-check-worktree` и др.). **adv-bot** — рабочий **project-local** срез того же семейства (общий `source_commit` в manifest tiriel / история bootstrap из central), сфокусированный на Python/WB и без локальной копии upstream-tree.

Оба репо разделяют идею: **продуктовые коммиты** (`/opsx-commit`, `openspec/`, `app/` или `src/`) отделены от **process-surfaces** (`/opsx-meta-commit`, allowlist в `.opsx/sources.yaml`).

## «Перенос» (transfer) знаний и команд между ветками/репо

В репозиториях это **не** «скопировать весь git», а **управляемый обмен process-plane**:

1. **Central (вне репо):** `sources.yaml` указывает `central_root` (типично `../opsx-central`) с `catalog/` и `sources/<repo>/<branch>/`.
2. **Публикация из целевого репо:** `/opsx-meta-update-snapshot` — снимок **этого** репо в central; `/opsx-meta-update-index` — обновление каталога; `/opsx-meta-commit` — локальный коммит только allowlisted путей.
3. **Получение в другой репо/ветке:** `/opsx-meta-import-command` — по умолчанию из **catalog index**, иначе явный donor; материализация в `.cursor/commands/**` и registry; staging и отчёты в `.opsx/runs/inbound/` (`DIFF_PACKET.md`, `MERGE_RECEIPT.md`).
4. **Жёсткие запреты при merge (зафиксированы в import и в истории inbound tiriel):**
   - не трогать `openspec/changes/**`, `openspec/archive/**`, продуктовый код (`src/**`, `app/**`, …);
   - **не** слепо перезаписывать `.opsx/upstream/**` (`central_update_policy: NEVER_OVERWRITE` в `manifest.yaml`);
   - donor-команды с «голым» canonical body vs local TARGET OVERRIDE — нужен Owner-выбор, иначе ломаются адаптеры (vue-npm vs poetry).
5. **Первичная посадка:** `/opsx-meta-bootstrap` тянет CORE/DEFAULT из central (`bootstrap-profile.md`); adv-bot прошёл это через `MERGE_RECEIPT` bootstrap step 4 (poetry adapter, без vue-npm как primary).

Итого **transfer** = bootstrap + import/snapshot/index по allowlist, с receipts, а не синхронизация продуктовых веток. Живой worktree merge для конкретного переноса — отдельная задача другого воркера.

## Минимальный каталог команд (для ориентации)

**Старт:** `/opsx` → `/opsx-pipeline` или `/opsx-meta`  
**Продукт:** `opsx-explore`, `opsx-new`, `opsx-ff`, `opsx-continue`, `opsx-update`, `opsx-bound-scope`, `opsx-apply`, `opsx-verify`, `opsx-archive`, `opsx-commit`  
**Качество (adv-bot сильнее в Python):** `opsx-test`, `opsx-pyright-strict-coverage`, `opsx-external-call-coverage`, `opsx-close-external-gap`, `opsx-devops`  
**Качество (tiriel):** `npm run build`, `opsx-browser-check`, Temporal `/tempo-verification` (см. `AGENTS.md`)  
**META:** `opsx-meta-bootstrap`, `opsx-projectize`, `opsx-meta-import-command`, `opsx-meta-update-snapshot`, `opsx-meta-fix-command-defects`, `opsx-meta-design-command`  
**Баги (оба, глубже в tiriel):** `opsx-fix-bug`, `opsx-bug-hunt`, `opsx-bug-team`, … — детали намеренно не разбираются здесь.

## Точки входа для чтения (без углубления в код)

- `AGENTS.md` — cloud/ветка/тесты (tiriel: browser handoff).
- `.cursor/commands/opsx.md`, `opsx-meta.md`, `opsx-pipeline.md`
- `.opsx/shared/meta-orientation.md`, `lifecycle.md`, `bootstrap-profile.md`
- `.opsx/manifest.yaml`, `.opsx/projectization.yaml`, `.opsx/sources.yaml`
- adv-bot: `.opsx/MERGE_RECEIPT.md` (пример bootstrap из central)
- tiriel: `.opsx/runs/inbound/*/DIFF_PACKET.md` (примеры политики merge)
