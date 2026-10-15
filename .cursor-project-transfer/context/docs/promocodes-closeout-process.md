# Закрытие change `promocodes-auth-server-redeem` (post-verify closeout)

Документ для Project OPSX: **упорядоченные gate’ы** от текущего состояния (verification in progress) до archive. Репозиторий-источник контрактов: `revoluxe-ai/tiriel-game` (`/agent/repos/tiriel-game`). Правки в game **не требуются** — только чтение команд и GRAPH.

**Owner (2026-09-30):** не спешить с `/opsx-archive` на промокодах. После verification ledger — отдельно Tempo bugbot и Tempo security («review»), затем **стоп на моделях**, project-gate’ы, `/opsx-verify mode=archive`, и только потом archive.

См. также: [рабочая инструкция OPSX §7.2](opsx-working-instruction.md#72-живой-продуктовый-чат-tiriel-промокоды), [preferences](../preferences.md).

---

## 0. Точка отсчёта (промокоды, 2026-09-30)

| Факт | Значение |
|------|----------|
| Change id | `promocodes-auth-server-redeem` |
| Worktree (Owner PC) | `fix/promocodes-issuance-redemption-20260927` |
| Apply | split-apply завершён (`IMPL_OK`, слайсы GREEN) |
| Verification | **в процессе**; ledger не `COMPLETE` |
| Известный блокер | `bank-promo-redemption×smoke_acceptance` — FAIL/BLOCKED (`PRODUCT_UI_GAP`) |
| Tempo verification | в том чате **ещё не** гоняли до терминала |
| Tempo bugbot / security | **ещё не** по Owner-порядку closeout |

Канонический GRAPH **не** включает `/tempo-bugbot` и `/tempo-security` между ledger и archive — для промокодов это **добавочный Owner-mandated** слой поверх spine.

---

## 1. Две оси: OPSX verification vs Tempo operator

| Ось | Команды | Полномочия |
|-----|---------|------------|
| **OPSX verification spine** | `/opsx-plan-verification` → `/opsx-next-check` → bounded executors **или** `/tempo-verification` | План `FROZEN`, ledger `VERIFICATION-LEDGER.json`, `ALL_REQUIRED_CHECKS_PASS` ≠ archive GO |
| **Tempo post-verify lanes** | `/tempo-bugbot`, `/tempo-security` | Diff `base..HEAD`, циклы review↔repair; **не** пишут archive GO |
| **Archive authority** | `/opsx-verify mode=archive` → `/opsx-archive` | Только `✅ GO` archive-verify авторизует archive |

Источники: `.cursor/pipeline/GRAPH.md` (`verification_ledger_complete --/opsx-verify mode=archive-->`), `.cursor/commands/_shared/tempo-pipeline.md`, `tools/temporal/pipelines.json`.

---

## 2. Карта команд (точные имена)

| Owner-фраза | Slash-команда | Внутренний review | Внутренний repair |
|-------------|---------------|-------------------|-------------------|
| tempo verification / ledger | `/tempo-verification change=<id> <next-check-tier> <executor-tier>` | `/opsx-next-check` | executor из `CHECK_ASSIGNMENT` |
| **tempo bugbot** | `/tempo-bugbot [base=stage] <review-tier> <repair-tier>` | **`/review-bugbot`** (native) | `/opsx-orch-bug-fix` |
| **tempo review** (security) | `/tempo-security [base=stage] <review-tier> <repair-tier>` | **`/review-security`** (skill) | `/opsx-bug-team` |
| (не путать) | `/opsx-security-review` | soft advisory в GRAPH | **не** заменяет `/tempo-security` |
| (не путать) | `/review-bugbot` вручную | без Temporal | без orch-цикла |

**Нет** отдельной команды `tempo-review` или `review-bugbot.md` в `.cursor/commands/` — bugbot/security идут только через `/tempo-*` + native `/review-bugbot` / skill `/review-security` внутри workflow.

Примеры tier’ов (оба обязательны): `low low`, `medium low`, `high low` — см. `tools/temporal/README.md`.

---

## 3. Упорядоченные gate’ы (от «verification in progress»)

Легенда: **M** = обязательный hard stop при нарушении; **O** = рекомендуемый/soft; **Owner** = ждём решения Owner.

### Фаза A — Довести verification ledger до COMPLETE **(M)**

Предусловие: `/opsx-plan-verification change=promocodes-auth-server-redeem` уже дал `plan_status=FROZEN` (если нет — сначала plan-verification, не archive).

1. **Прогон checks** — **M**, выбор одного:
   - **Оператор:** `/tempo-verification change=promocodes-auth-server-redeem <tier> <tier>` до `ALL_REQUIRED_CHECKS_PASS` или явного FAIL/BLOCKED.
   - **Ручной spine:** цикл `/opsx-next-check` + только назначенные bounded executors (`/opsx-run-tests`, `/opsx-browser-check`, …).

2. **Cloud browser handoff** на `smoke_acceptance` — **M** на Cloud VM: Tempo **останавливается**; parent agent делает `/opsx-browser-check`, `verify/check-results/**`, `verify/BROWSER-CHECK.md`, reconcile:
   `node .opsx/tools/opsx-verification-ledger.mjs reconcile --change promocodes-auth-server-redeem`, затем снова `/tempo-verification`. Протокол: `tools/temporal/CLOUD-BROWSER-HANDOFF.md`, `AGENTS.md`.

3. **Текущий блокер промокодов** — **M**: закрыть `PRODUCT_UI_GAP` на smoke (продукт/сценарий), reconcile, пока `ledger_status` ≠ `COMPLETE` для frozen `plan_id` + snapshot digest.

4. **Терминал tempo-verification** — **O**: `owner-done-signal` в Owner Chrome (не путать с browser-release после smoke).

**Запрещено:** считать `ALL_REQUIRED_CHECKS_PASS` или tempo PASS достаточным для archive (`tempo-verification.md`: не auto `/opsx-verify`).

---

### Фаза B — Tempo bugbot **(M для промокодов по Owner)**

После **`VERIFICATION-LEDGER.json` → `ledger_status=COMPLETE`** (то, что Owner называет «verification ledger complete»):

```text
/tempo-bugbot [base=stage] <review-tier> <repair-tier>
```

- `head` = текущая ветка (auto); `change=` **не** передаётся.
- Терминалы: `BUGBOT_CLEAN` (PASS), `NO_REPAIR_PROGRESS`, `MAX_ROUNDS_REACHED`, `STALLED` — см. `pipelines.json`.
- Артефакт прогона: `.opsx/runs/temporal/runs/*.json` (и UI Temporal) — **операционный ledger прогона**, не `VERIFICATION-LEDGER`.

**Owner stop:** при `FAIL`/`BLOCKED` или остаточных MUST_FIX — repair через orch, повтор `/tempo-bugbot`; **не** переходить к archive.

---

### Фаза C — Tempo security («tempo review») **(M для промокодов по Owner)**

```text
/tempo-security [base=stage] <review-tier> <repair-tier>
```

- Scope: `src/**`, `tests/**` только.
- **Не** вызывать `/opsx-security-review` или `/opsx-orch-bug-fix` вместо этого пайплайна.

Терминал чистоты: `SECURITY_CLEAN`. Аналогично — зафиксировать STATUS в отчёте Owner по шаблону `tempo-pipeline.md`.

---

### Фаза D — Checkpoint моделей **(M — стоп для Owner)**

**Перед** финальным closeout (и **перед** первым запуском фаз B/C, если tier’ы ещё не согласованы):

| Слой | Ожидание контракта | Правило Owner (2026-09-30) |
|------|-------------------|----------------------------|
| Tier-токены | Последние два аргумента: `low` \| `medium` \| `high` | Owner выбирает пару явно в slash |
| Резолв модели | `tools/temporal/agent-models.json` (+ optional `.opsx/runs/temporal/config/agent-models.overlay.json`) | На **vkita-pc** и субагентах — **только `composer-2.5` standard** |
| Текущий game default | Все tier’ы в `agent-models.json` → `cli_model: composer-2.5` | Совпадает с Owner rule |
| Риск | Старые run JSON с `model: auto` / grok-fast | **Owner:** сверить overlay и фактический `agent --model` в worker; при расхождении — **стоп**, выставить overlay под composer-2.5, **не** archive |

**Действие на стопе:** Owner подтверждает обе пары tier’ов для bugbot и security (часто `low low` на локали) и что worker читает composer-2.5. Агент **не** подменяет high/grok без явного Owner.

README допускает **лестницу** отдельными вызовами (`low low` → `medium low` → `high low`) — для промокодов по умолчанию достаточно одного прохода `low low`, если Owner не заказал ladder.

---

### Фаза E — «Project проверки» **(M где указано)**

| Проверка | Команда / файл | Когда | Смысл |
|----------|----------------|-------|--------|
| **Projectization** | `.opsx/projectization.yaml` | verify + archive write | `status: COMPLETE`, `normal_commands_enabled: true` — иначе **FAIL_CLOSED** → `/opsx-projectize` (не полный re-projectize на game сейчас) |
| **Quality gates** | `.opsx/project/quality-gates.md` | read в `/opsx-verify`, `/opsx-archive` | Каталог возможностей; не заменяет frozen verification plan |
| **Plan verification** | `/opsx-plan-verification` | **до** фазы A (уже должно быть) | `FROZEN` план; это **не** «projectize», а freeze TARGET×CHECK |
| **Projectize apply** | `/opsx-projectize:GO` | только если lock `REQUIRED` | На tiriel-game сейчас **COMPLETE** — повторный GO **запрещён** без Owner reset |
| **Doctor** | `/opsx-doctor` | **O**, чаще post-archive | Hygiene active tree; **не** gate promocodes closeout |
| **Project bug hunt** | `/tempo-project-bug-hunt change=…` | **O** advisory pre-PR (GRAPH) | **Не** требуется для archive promocodes, если Owner не заказал |

Итого «project проверки» перед close = **убедиться, что projectization COMPLETE** (и verify/archive не возвращают `OPSX_PROJECTIZATION_REQUIRED`), плюс frozen plan/ledger согласованы — **не** смешивать с `/opsx-projectize:GO`.

---

### Фаза F — Archive verify **(M)**

```text
/opsx-verify change=promocodes-auth-server-redeem mode=archive
```

Hard stops (кратко):

- Нужен недавний archive-verify с маркером **`✅ GO`** (не `IMPL_OK` alone).
- `ledger_status=COMPLETE` + frozen plan identity + structural scenario coverage.
- `PRODUCT_ACCEPTANCE` по `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`.
- Semantic write-target / incomplete planning — см. тело `/opsx-archive`.

`mode=impl` — DoD audit, **не** авторизует archive.

---

### Фаза G — Archive **(M, только после F)**

```text
/opsx-archive promocodes-auth-server-redeem
```

Hard stops: archive-verify `✅ GO`, proposal|design|specs `done`, PA PASS/NOT_REQUIRED, ADL/promote decisions, delta spec sync prompt.

**Owner (2026-09-30):** не вызывать archive сразу после tempo-verification или bugbot — только после фазы F.

**O после успеха:** `/opsx-distribute-brief`, `/opsx-estimate` (soft в archive command).

---

## 4. Сводная последовательность (one page)

```text
[СЕЙЧАС] verification in progress (smoke gap)
    ↓ M
/tempo-verification …  (+ Cloud handoff на smoke)  → ledger COMPLETE
    ↓ M (Owner promocodes)
CHECKPOINT моделей (composer-2.5, tier пары)
    ↓ M (Owner promocodes)
/tempo-bugbot …  → BUGBOT_CLEAN (или Owner решает остаток)
    ↓ M (Owner promocodes)
/tempo-security …  → SECURITY_CLEAN
    ↓ M
projectization COMPLETE (+ frozen plan уже valid)
    ↓ M
/opsx-verify mode=archive  → ✅ GO
    ↓ M
/opsx-archive
```

---

## 5. Что останавливает Owner

| Ситуация | Действие |
|----------|----------|
| Модели / overlay не composer-2.5 | Стоп фаз B–G; правка overlay + подтверждение tier’ов |
| smoke / ledger не COMPLETE | Стоп archive; `/opsx-apply` / `/opsx-update` / browser-check по маршруту verify |
| bugbot/security FAIL | Стоп closeout; orch/bug-team, повтор tempo |
| verify archive `NO_GO` | Маршрут из verify (next-check, apply, PA, scenario) — **не** archive |
| Открытые `- [ ]` в tasks.md | Archive ждёт `CONTINUE_ARCHIVE_INCOMPLETE` (точный токен) |

---

## 6. Ссылки на файлы (tiriel-game)

- Tempo kernel: `.cursor/commands/_shared/tempo-pipeline.md`
- Команды: `.cursor/commands/tempo-verification.md`, `tempo-bugbot.md`, `tempo-security.md`
- Pipelines: `tools/temporal/pipelines.json`, `tools/temporal/README.md`
- Модели: `tools/temporal/agent-models.json`
- Verify / archive: `.cursor/commands/opsx-verify.md`, `opsx-archive.md`
- Plan: `.cursor/commands/opsx-plan-verification.md`
- Projectize: `.cursor/commands/opsx-projectize.md`
- GRAPH post-verify: `.cursor/pipeline/GRAPH.md` (§ edges `verification_ledger_complete`, Terminal / recovery ~1817)

---

*Подготовлено read-only по `/agent/repos/tiriel-game`, 2026-09-30. Без PR и без правок репозитория.*
