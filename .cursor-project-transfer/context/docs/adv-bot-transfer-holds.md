# Удержания переноса OPSX game → adv-bot

**Репозиторий:** `C:\Users\vkita\my_code\meta-repo\adv-bot-full-command-transfer`  
**Ветка:** `feature/opsx-full-command-transfer`  
**Источник:** `game` @ `91311ada…` (100 команд `.cursor/commands/*.md`)  
**Источники учёта:** `.opsx/registry/command_transfer_manifest.md` (актуальнее по содержимому), `.opsx/registry/command_transfer_completion.json` (снимок `2026-09-30T09:57Z`)

## Когда перенос можно считать завершённым

По `command_transfer_completion.json` перенос **ещё не закрыт**:

| Критерий | Значение |
|---|---|
| `status` | `TRANSFER_SURFACE_MATERIALIZED_WITH_BOUNDED_HOLDS` |
| `claims.functional_parity_claimed` | `false` |
| `claims.production_ready_claimed` | `false` |
| `claims.merge_authorized` | `false` |

Поверхность команд материализована (все 100 имён SOURCE на TARGET, коллизии учтены), контрактные pytest/bounded-verify для переноса в основном зелёные, Temporal SDK-активация для четырёх `tempo-*` задокументирована. **Семантическая паритетность и merge в adv-bot не заявлены.**

Дополнительно вне scope «готовности переноса», но в completion: baseline `git_packaging_contract` 23/25 (P15, G25 — `opsx-create-pr` / GRAPH), файлы transfer не трогал.

## Счётчики по состояниям (manifest, 100 команд)

| Состояние | Кол-во | Смысл для «finished» |
|---|---:|---|
| `FUNCTIONAL_PROVEN` | **16** | Закрыто: есть evidence исполнения / целевой runtime (не только статика) |
| `IMPLEMENTED_UNVERIFIED` | **23** | Код/команда на месте; **нужен live run** → `FUNCTIONAL_PROVEN` |
| `EXISTING_ADAPTATION_REQUIRED` | **61** | Same-name TARGET защищён; нужна **поштучная** сверка authority/поведения с SOURCE (Poetry/WB vs vue-npm и т.д.) |

**Не закрыто:** 84/100 (61 + 23).  
**Закрыто по manifest:** 16/100.

### Расхождение с `command_transfer_completion.json`

В JSON в блоке `manifest.states` зафиксировано: `FUNCTIONAL_PROVEN` 4, `SOURCE_STAGED_MIGRATION_HOLD` 12, плюс те же 61/23. В **текущем** `command_transfer_manifest.md` состояния `SOURCE_STAGED_MIGRATION_HOLD` **нет** — 12 ранее staged-команд (цепочка `opsx-apply-*`, `opsx-browser-check`, orch/post-deploy/security-learn, четыре `tempo-*`) отражены как **`FUNCTIONAL_PROVEN` (итого 16)**. Для планирования опираться на manifest; completion.json обновить при следующем freeze completion.

### Другие состояния

- **`SOURCE_STAGED_MIGRATION_HOLD`:** только в устаревшем снимке completion, не в актуальном manifest.
- **Target-only:** в inventory `target_only_commands: 12` — команды adv-bot, не входящие в ledger 100 SOURCE (отдельный учёт, не строки manifest).

## Группы удержаний (что осталось сделать)

### 1. `EXISTING_ADAPTATION_REQUIRED` — 61

Защита существующей adv-bot реализации до доказанной семантической reconcile. Типовые gap:

- адаптеры и quality gates (**vue-npm** в SOURCE vs **Poetry/pyright** на TARGET);
- status-resolved `planningHome` / `changeRoot` / owner-contract;
- bug-episode, bounded-verify authority (S6: `opsx-next-check`, `opsx-plan-verification`, `bounded-executor`);
- WB/devops/production safety без фактических prod-проверок в transfer-run.

**Примеры команд:** `opsx`, `opsx-adapt-project`, `opsx-new`, `opsx-ff`, `opsx-update`, `opsx-verify`, `opsx-archive`, `opsx-supervisor`, `opsx-static-check`, `opsx-meta-import-command`, `opsx-resolve-conflict`.

### 2. `IMPLEMENTED_UNVERIFIED` — 23

Установлено и частично покрыто тестами; manifest явно требует **исполнение команды в этом run** (не только static). Частые подтипы:

- READ_ONLY маршруты с делегированием на защищённые writer (`opsx-bug-intake-clear` → materialize, disposition/family-plan без SOURCE GO-writes);
- **integration gaps** (unwired consumers): `opsx-intent-align`, `opsx-risk`, `opsx-ts-design` / `opsx-ts-review` vs `/opsx-new`/`/opsx-ff`/`/opsx-continue`;
- **mode=bounded** / S6 registration: `opsx-run-tests`, `opsx-run-typecheck`, `opsx-run-build`, `opsx-security-review`;
- **parity PARTIAL:** security triage/review, models (Temporal config), meta-add-command (P0–P11 blocked).

**Примеры команд:** `opsx-doctor`, `opsx-plan`, `opsx-bugbot-report`, `opsx-bug-intake-clear`, `opsx-risk`, `opsx-run-tests`, `opsx-security-triage`, `opsx-meta-update-all-snapshots`, `opsx-sherlock`.

### 3. `FUNCTIONAL_PROVEN` — 16 (сделано)

**Примеры:** `opsx-apply-red` … `opsx-apply-scaffold`, `opsx-browser-check`, `opsx-control-plane-security-review`, `opsx-orch-bugbot-converge`, `opsx-orch-bug-fix`, `opsx-post-deploy-acceptance`, `opsx-security-learn`, `tempo-bugbot`, `tempo-project-bug-hunt`, `tempo-security`, `tempo-verification`.

`remaining_holds_activation.json` (10:53Z) детализирует runtime-активацию подмножества non-tempo proven-команд; полный список proven — в manifest.

## Чеклист до «transfer finished»

1. Свести **23** `IMPLEMENTED_UNVERIFIED` → `FUNCTIONAL_PROVEN` (live runs + обновление manifest).
2. Пройти **61** `EXISTING_ADAPTATION_REQUIRED` (reconcile + снятие hold или документированная целевая дельта).
3. Пересобрать `command_transfer_completion.json`: `functional_parity_claimed`, `merge_authorized`, финальный `status`.
4. Решить судьбу **12 target-only** команд и merge в основной adv-bot (вне 100-ledger, но влияет на «полный» OPSX на продукте).
5. Опционально: baseline P15/G25 packaging — не блокер transfer в completion, но влияет на PR hygiene.

## Рекомендуемый первый hold

**`opsx-doctor`** (`IMPLEMENTED_UNVERIFIED`): read-only CHECK, уже реализован; live run даёт низкий риск и снимает зависимость, отмеченную для `opsx-meta-export-pack` («`/opsx-doctor` remains an unresolved optional dependency»). После успешного run — обновить строку manifest и двигаться по остальным 22 unverified или параллельно планировать reconcile для `opsx` (корневой router, `EXISTING_ADAPTATION_REQUIRED`).
