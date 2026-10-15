# ADV Bot — обязательный порядок разработки

Canonical development workflow для обычных изменений `adv-bot`.  
Исключение — аварийный production hotfix (см. [Отклонение 2026-09-30](#отклонение-2026-09-30)). Иначе — **OPSX**, command-only (см. [opsx-working-instruction.md](opsx-working-instruction.md), [preferences.md](/cursor/stores/self/preferences.md)).

**Обновлено:** 2026-09-30 (Owner contract, USER_ASSERTED)

**Связь:** [adv-bot-strategic-coordinator-role.md](adv-bot-strategic-coordinator-role.md) · [adv-bot-local-worktrees.md](adv-bot-local-worktrees.md)

---

## 1. Базовая ветка

- Репозиторий: `C:\Users\vkita\my_code\meta-repo\adv-bot`
- Базовая линия для новых changes: **локальная** ветка `stage` (текущий `HEAD` на диске), не подменять автоматически на `origin/stage` без явного Owner-решения.
- Перед созданием worktree координатор/агент фиксирует: `git branch --show-current`, `git rev-parse HEAD`, `git status`, что `stage` — ожидаемая база.
- При создании feature-worktree **не переключать и не коммитить в `adv-bot/stage`** ради подготовки change — `stage` остаётся integration checkout, пока Owner не выбрал иной режим.

---

## 2. Один change = одна ветка = один worktree

- Canonical **change id** = имя OpenSpec change и имя ветки: `drr-percent-cpo`, `clickhouse-migrations-control-plane`, `web-admin-v0`, …
- **MUST (новые changes):** `branch_name == worktree_directory_name` — каталог worktree под `meta-repo\` совпадает с именем ветки **без** префикса `feature/` (legacy ветки с `feature/` не переименовывать задним числом без Owner).
- Путь worktree: `C:\Users\vkita\my_code\meta-repo\<change-name>`
- Один активный change — один изолированный worktree и один чат/hop product apply; не смешивать соседние changes «потому что про рекламу».

---

## 3. Создание worktree

Порядок (Owner contract):

1. Старт из `adv-bot` на локальной `stage` (чистая или осознанно dirty — зафиксировать в отчёте).
2. Создать ветку `<change-name>` от текущего `stage` HEAD.
3. `git worktree add` → `C:\Users\vkita\my_code\meta-repo\<change-name>` на эту ветку.

Перед `/opsx-new` / `/opsx-ff` / implementation проверить: путь существует, ветка совпадает с change id, `git status` понятен, HEAD зафиксирован. При расхождении path/branch/change id — **NO_GO**, implementation не начинать.

---

## 4. Implementation только в worktree change

- Product writes (`app/**`, миграции change, тесты change) — **только** в worktree данного change.
- Запрещено как норма: feature-код в `adv-bot/stage`, в соседнем worktree другого change, в случайном Cursor cloud checkout без привязки к change id.
- Read-only preflight/investigate в `stage` или через `/opsx-devops` — допустимо; apply — только после GO в правильном worktree.

---

## 5. OPSX (command-only lifecycle)

Разработка ведётся **только** через slash-команды `.cursor/commands/opsx-*.md` (и `/tempo-*` где зафиксировано для участка). Прямых правок продукта/контрактов без команды, разрешающей шаг, нет.

Типичный spine (масштабировать для малых changes, verification не пропускать):

1. Preflight / inventory (read-only где требует команда)
2. Owner Contract + planning artifacts (`proposal`, `design`, `spec`, `tasks`)
3. `/opsx-apply` (implementation) в worktree change
4. Bounded verify: `/opsx-plan-verification` → ledger checks → при необходимости `/tempo-verification`
5. `/opsx-verify` (read-only audit перед archive)
6. Merge readiness / merge в локальную `stage` — только после явного `GO_FOR_MERGE` (§9)

Мета-развитие OPSX (tiriel-game) и product apply adv-bot — **разные hops**, не смешивать без порядка Owner.

---

## 6. Перед implementation (обязательный чеклист)

Зафиксировать в hop (FACT / USER_ASSERTED / UNKNOWN):

| Проверка | Зачем |
|----------|--------|
| Base `stage` HEAD | Provenance ветки change |
| Worktree path + branch + `git status` | Соответствие §2–3 |
| Sibling worktrees / collision map | Не трогать чужой dirty; CH migration numbers, semantic owner |
| OpenSpec change id + `openspec/changes/<id>/` | Один change |
| Architecture decisions (context-first) | Placement, write-path |
| Tests / gates из tasks | Scope regression |

Зоны повышенного collision: ComplexAdv, PlanData, bidder, V3 updater, WB shop runner, ClickHouse migrations (`006+` только через назначенный change).

---

## 7. Implementation

- Писать код строго в scope change и tasks; ownership по decisions.
- Соблюдать project gates: pytest (unit/integration по маркерам), `poetry run pyright-strict` когда команда требует, `_ =` для non-None discard (см. repo `AGENTS.md`).
- Коммит/push — по явному запросу Owner или контракту команды; не считать merge/archive автоматическими следствиями apply.

---

## 8. Verification перед merge readiness

До заявления «готово к merge»:

- Targeted tests из change + релевантный regression по затронутым модулям
- Static checks (pyright и др. — по VERIFY_POLICY / команде)
- Spec acceptance / tasks checklist
- Review `git diff` и `git status` в worktree change (нет постороннего scope)

`FROZEN` verification plan ≠ PASS; archive — отдельный `/opsx-archive` после `/opsx-verify`.

---

## 9. Merge и выкат (Owner contract 2026-09-30)

После явного **`GO_FOR_MERGE`** и §8 verification:

1. **stage → master** — только если `stage` стабильно в prod **≥24h**, нет новых багов/деградаций (Owner judgment).
2. **Feature/fix → `stage`** — merge change-ветки (например hotfix PR) в `stage` после зелёных gates (или Owner GO на migration-gate).
3. **Выкат** — **`/opsx-devops`**: CONTROL → migrate при необходимости → CAS entrypoints (`adv-bot-asq-worker`, …); не blind restart proxy.
4. **Rollback при плохой раскатке нового образа** (Owner 2026-09-30): откат на **резерв с `master`** (LKG / prepared fallback из OPS_STATE), не чинить prod на месте и не угадывать тег.

Локальная `stage` остаётся integration checkout; remote push и prod — только через команды и Owner GO где требует контракт.

---

## Отклонение 2026-09-30

[PR #443](https://github.com/revoluxe-ai/adv-bot/pull/443): ветка `cursor/create-complex-advs-telegram-resilience-6147` ведётся в checkout `C:\Users\vkita\my_code\meta-repo\adv-bot`, **без** отдельного worktree `meta-repo/<change-name>`.

**Классификация:** emergency hotfix deviation (инцидент nmid 138252141, [PAT-ADV-001](/cursor/stores/self/internal/recurring-patterns.md)); не использовать как шаблон для новых changes.

**После merge:** рассмотреть ретро-именование worktree/ветки под §2 или задокументировать постоянное исключение в store; все **новые** changes — снова строго §2–4.

---

*Координатор adv-bot обязан отклонять hops, нарушающие §2 (имя ветки ≠ каталог worktree, `feature/` для новых changes), и ссылаться на этот документ.*
