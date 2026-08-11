## Context

В настройках РК два автоматических пути записи ставки Авто:

1. **«Управление ставкой»** → внутри подменю **«Включить/Выключить управление ставкой для Авто»** (`bidder_for_auto` → legacy bidder / CPM path для Авто-ноги).
2. **«Управление ставкой в полках»** → **«Включить/Выключить управление»** (`auto_shelf_bid_control_enabled` → `AutoShelfBidControlManager` / `set_bid`).

Owner rule: если **«Управление ставкой в полках»** включено — путь **«управление ставкой для Авто»** игнорируется (не меняет ставку). Нужно закрепить ownership (proposed decision), thin spec и доказать paired ON/OFF; алгоритм выбора ставки / plan_distance не переписываем.

Наблюдение runtime (для characterization): корутина полок уже фильтрует по `auto_shelf_bid_control_enabled`; legacy путь «для Авто» в bidder **не** обязан сегодня пропускать запись при включённых полках — gap возможна и проверяется tests-first.

Стек: Python 3.11, shop-runner, AdvSetting flags, WB bid setters. Linked: `INC-AUTO-COST-SHELF-COEXIST-01`.

## Goals / Non-Goals

**Goals:**

- Зафиксировать и доказать взаимное исключение automated записи ставки Авто между двумя UI-путями (вкл/выкл **«Управление ставкой в полках»**).
- Если runtime нарушает правило — минимальный gate до write boundary на старом пути при включённых полках (без rewrite selection/plan_distance).
- Различимость: запись ставки полок ≠ activity cost-пауза (`cost_rule_failed`).
- Tests-first: characterization текущего поведения + paired regression обоих режимов.

**Non-Goals:**

- Терминальная пауза «ставки в полках исчерпаны» / retest epoch.
- Empty-keywords Search, billing ног, тариф 1000₽, comms, disconnect, onboard.
- Retire updater v2; смена «стандартный / кластерный биддер»; режим раскрутки РС.
- Перепись plan_distance / shelf selection math.
- Расширение DoD на UI copy redesign.

## Architecture Decision References

- `openspec/changes/pin-legacy-autobidder-vs-shelf-coexistence/decisions/auto-bid-module-coexistence-write-path/decision.md` (Proposed) — SoT ownership взаимного исключения bid-write; reason split с cost-паузой; forward-compat без маскировки terminal shelf под `cost_rule_failed`.
- `openspec/decisions/empty-keywords-pause-write-path/decision.md` (Accepted) — ортогонален (Search empty-keywords); не владеет этим mutual-exclusion.
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` (Accepted) — defaults overlays не место для этого gate.
- A/B Hold: freeze ≠ stop — ортогонален; не stop/start writer этого контракта.

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|---|---|---|
| Automated запись ставки при **«Управление ставкой в полках»** вкл | shelf bid control write-path (`AutoShelfBidControlManager` → setter) | успешная запись ставки Авто через путь **«управление ставкой для Авто»** |
| Automated запись ставки при **«Управление ставкой в полках»** выкл и **«для Авто»** вкл | legacy bidder / CPM path, gated by `bidder_for_auto` | shelf control запись ставки |
| Gate «полки вкл → старый ignore» | shop-runner orchestration / bidder entry до WB bid write (минимальный skip) | только текст UI; mode-defaults; empty-keywords path; Hold freeze |
| Cost pause/start (`cost_rule_failed`) | activity-control | выдавать себя за запись ставки полок; маскировать будущий terminal shelf reason |
| Selection / plan_distance | без изменений в этом change | rewrite «заодно» |

Placement MUST match proposed `auto-bid-module-coexistence-write-path`.

## Semantic Write Target (RESOLVED)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: automated запись ставки ноги Авто («для Авто» vs «в полках»)
TARGET_ENTITY_OR_LEG: Auto-leg bid on Wildberries
ALLOWED_ADAPTERS:
  - auto_shelf_bid_control_enabled=true → AutoShelfBidControlManager set_bid / _set_target_bid
  - auto_shelf_bid_control_enabled=false AND bidder_for_auto=true → wb_api.update_cpm(auto_adv_id, …) legacy bidder path
FORBIDDEN_ADAPTERS:
  - auto_shelf_bid_control_enabled=true → wb_api.update_cpm(auto_adv_id, …) via «управление ставкой для Авто»
  - auto_shelf_bid_control_enabled=false → shelf set_bid write
TARGET_EVIDENCE: owner-contract.md; proposal Desired behavior; decision auto-bid-module-coexistence-write-path; spec auto-bid-module-coexistence
OWNER_DECISION_SOURCE: openspec/changes/pin-legacy-autobidder-vs-shelf-coexistence/owner-contract.md (Решения Owner)
REQUIRED_PAIRED_TESTS: shelf ON → legacy Auto update_cpm blocked; shelf OFF → legacy Auto update_cpm allowed / shelf not writing
```

## OWNER_LIFECYCLE_ECHO

Упорядоченный смысл во времени (Owner Contract):

1. Пользователь в настройках РК задаёт **«Управление ставкой для Авто»** и/или **«Управление ставкой в полках»**.
2. На тике shop-runner оба модуля *могут* иметь повод писать ставку Авто.
3. Если **«Управление ставкой в полках»** включено — ставку Авто меняет только он; путь **«для Авто»** не доводит запись до успеха.
4. Если **«Управление ставкой в полках»** выключено — он ставку не пишет; при включённом **«для Авто»** старый путь MAY писать ставку Авто.
5. Пауза/старт по себестоимости (`cost_rule_failed`) остаётся отдельным контуром и не подменяет запись ставки полок.

`CONFIRM_LIFECYCLE`: **confirmed** (Owner, 2026-08-11) — echo accepted; production gate apply allowed.

## Decisions

1. **Pin-then-gate, не rewrite.** Сначала characterization: кто реально пишет ставку при обоих флагах. Если при включённом **«Управление ставкой в полках»** путь **«для Авто»** всё ещё успешно пишет — добавить узкий skip/ignore до write; не трогать math выбора ставки полок.

2. **Источник истины флагов.** UI-смысл ↔ settings: `auto_shelf_bid_control_enabled` = **«Управление ставкой в полках»**; `bidder_for_auto` = **«Управление ставкой для Авто»** внутри **«Управление ставкой»**. Контракт — про эти два флага и их writers, не про переключатель кластерного биддера.

3. **Где ставить ignore на старом пути.** Предпочтительно самый узкий seam, где путь **«для Авто»** решает писать ставку Авто-ноги (bidder / update CPM path), conditioned on `auto_shelf_bid_control_enabled`. Альтернатива — фильтр кандидатов корутины — хуже, если тот же bidder обслуживает Search/другие режимы; не отключать лишнее.

4. **Cost-пауза не в DoD rewrite.** Activity-control может по-прежнему паузить/стартовать Auto с `cost_rule_failed`; этот change не меняет формулу cost-rule и не вводит terminal shelf reason. Только запрет маскировки bid-write полок под cost reason в контракте/тестах различимости.

5. **Validation.** Paired unit tests:
   - полки выкл + «для Авто» вкл → старый writer MAY вызвать set/update ставки Авто; shelf setter не вызывается;
   - полки вкл → shelf writer MAY; старый «для Авто» writer MUST NOT успешную запись;
   - (smoke) cost pause reason / ControlReason полок не подменяют друг друга в assertions контракта.

Alternatives considered:

- Переписывать bidder selection при полках ON — отклонено (scope / HARD).
- Считать coexistence «уже ок», потому что cost watchdog ветвится по полкам — отклонено: Owner контракт про **запись ставки**, не про cost pause CPO input.
- Класть gate в Telegram handlers — отклонено: UI не останавливает shop-runner writers.

## Risks / Trade-offs

- [Оба writer’а уже пишут при полках вкл] → characterization сначала; gate на старом пути; paired regression падает без gate.
- [Слишком широкий skip отключит Search CPM / не-Авто ветки того же bidder] → gate только для Авто-ноги / `bidder_for_auto` write, не глобальный off bidder.
- [Смешение с cost_rule_failed в tasks] → HARD scope; tests не требуют смены cost formula.
- [Ложное чувство «pin only» без runtime fix] → если gap подтверждена, apply MUST закрыть gate, иначе NO_GO.

## Migration Plan

1. Spec + tests (characterization / paired) — красные при нарушении Owner rule.
2. Минимальный gate на старом path при `auto_shelf_bid_control_enabled`, если нужно.
3. Зелёные paired tests; без миграций БД / без нового reason code.
4. Rollback: откатить gate-commit; флаги UI и shelf control без изменений схемы.

Performance: один bool-check на тик старого path — negligible.

## Open Questions

- Точный seam skip на legacy path (подтвердить characterization: `bidder_func` / `run_bidder_process_for_adv` / иной Auto CPM writer) — закрывается в apply tests-first, не блокирует design.
- Нужен ли отдельный log/skip_reason при ignore старого path — желательно для диагностики, не обязателен для DoD контракта.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`auto-bid-module-coexistence-write-path`)
- [x] implementation layer matches decision (`bidder_func.run_bidder_process_for_adv` Auto write gated; `/opsx-apply` 2026-08-11)
