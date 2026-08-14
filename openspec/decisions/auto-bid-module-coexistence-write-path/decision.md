# Decision: auto-bid-module-coexistence-write-path

## Status

Accepted

## Context

В paid UI настроек РК рядом живут два автоматических пути записи ставки Авто:

1. Старый: главное меню → **«Управление ставкой»** → внутри подменю
   **«Включить/Выключить управление ставкой для Авто»**.
2. Новый: главное меню → **«Управление ставкой в полках»** →
   **«Включить/Выключить управление»**.

Нужен reusable ownership: кто имеет право automated-записью менять ставку Авто,
когда включены оба UI-пути, и как эта запись отличается от паузы/старта по
себестоимости (activity-control / `cost_rule_failed`), чтобы модули не писали
ставку одновременно и не подменяли друг друга reasons.

## Decision

Запись ставки Авто при конкуренции «управление ставкой для Авто» vs
«управление ставкой в полках» принадлежит **взаимно исключающему write-path
контракту** capability `auto-bid-module-coexistence`:

1. **Shelf-enabled gate.** Когда управление ставкой в полках **включено**,
   единственный allowed automated writer ставки Авто для этого режима —
   write-path **«Управление ставкой в полках»**. Write-path **«управление
   ставкой для Авто»** MUST быть ignored (MUST NOT доходить до успешной
   automated записи ставки Авто).
2. **Shelf-disabled gate.** Когда управление ставкой в полках **выключено**,
   write-path полок MUST NOT писать ставку; при включённом «управлении ставкой
   для Авто» старый write-path MAY писать ставку Авто.
3. **Reason / surface split.** Внутренние причины цикла полок и activity
   reason cost-паузы (`cost_rule_failed` и соседние budget/cost reasons)
   MUST оставаться различимыми: запись ставки полок MUST NOT маскироваться
   под cost-паузу; cost-пауза MUST NOT выдавать себя за действие модуля полок.
4. **Orthogonal contours.** Контроль активности (pause/start ноги Auto),
   A/B Hold freeze (freeze ≠ stop), Search empty-keywords pause — **не**
   владельцы этого mutual-exclusion bid-write контракта; они не заменяют
   gates п.1–2.
5. **Forward-compat.** Будущий terminal reason «полки исчерпаны / нет плана»
   MUST NOT вводиться через маскировку под ordinary `cost_rule_failed` и MUST
   NOT жить внутри write-path «управление ставкой для Авто». Ownership
   terminal shelf pause — отдельный future decision/change.
6. **Non-goals of this ownership.** Decision не переносит selection /
   plan_distance math и не меняет смысл переключателя «стандартный /
   кластерный биддер».

## Applies to

- Capability `auto-bid-module-coexistence`
- Automated bid writers, связанные с UI **«управление ставкой для Авто»** и
  **«Управление ставкой в полках»**
- Shop-runner / activity orchestration, которая выбирает, какой bid writer
  активен при включённом / выключенном **«Управление ставкой в полках»**
- Paired characterization/regression этого coexistence контракта
- Future changes, добавляющие terminal shelf pause / distinct Auto reason
  (MUST уважать п.3 и п.5)

## Allowed

- В **«Управление ставкой в полках»** нажали **«Выключить управление»**, а в
  **«Управление ставкой»** включено **«Управление ставкой для Авто»** → старый
  путь MAY менять ставку Авто; путь полок MUST NOT менять ставку.
- В **«Управление ставкой в полках»** нажали **«Включить управление»** → путь
  полок MAY менять ставку; **«Управление ставкой для Авто»** MUST NOT менять
  ставку (игнорируется до write boundary).
- Хранить и логировать причины цикла **«Управление ставкой в полках»** отдельно
  от `cost_rule_failed` / activity pause reasons
- Читать включённость **«Управление ставкой в полках»** как gate взаимного
  исключения
- Минимальный gate-fix без rewrite алгоритма выбора ставки

## Forbidden

- Когда **«Управление ставкой в полках»** включено — успешная automated запись
  ставки Авто и старым путём (**«для Авто»**), и новым одновременно
- Реализовывать «игнор старого» только в UI-тексте без runtime gate до write
- Маскировать запись ставки из **«Управление ставкой в полках»** или будущую
  терминальную паузу полок под `cost_rule_failed` (или иной ordinary
  cost/budget reason) как единственный durable reason
- Класть ownership этого mutual-exclusion в mode-defaults overlays,
  empty-keywords write-path или A/B Hold freeze path
- Переписывать selection / plan_distance «заодно» под видом coexistence
- Смешивать scope с billing ног, тарифом, disconnect, Search empty-keywords DoD

## Examples

Good:

- **«Управление ставкой в полках»** включено → пишет ставку только он;
  **«Управление ставкой для Авто»** не доводит запись ставки до успеха
- **«Управление ставкой в полках»** выключено → он ставку не пишет; при
  включённом **«Управление ставкой для Авто»** старый путь пишет ставку как
  раньше
- Контроль активности пишет `cost_rule_failed` при pause — это не reason
  записи ставки из **«Управление ставкой в полках»**

Bad:

- **«Управление ставкой в полках»** включено, и оба пути успешно меняют ставку
- Сбой/исчерпание ставок полок записан как `cost_rule_failed`
- Search empty-keywords path «чинит» сосуществование этих двух bid writers

## Related specs

- `openspec/specs/auto-bid-module-coexistence/spec.md`
- Ортогонально (не SoT этого decision):
  `openspec/specs/pause-on-empty-keywords/spec.md`

## Related changes

- `openspec/changes/archive/2026-08-11-pin-legacy-autobidder-vs-shelf-coexistence`
  (introduced; promoted 2026-08-11)
- Evolution: `openspec/evolution/affordable-auto-pause-on-empty.md`
  (`INC-AUTO-COST-SHELF-COEXIST-01`; forward
  `INC-AUTO-SHELF-PAUSE-01` — out of scope)
- Ортогональность empty-keywords:
  `openspec/decisions/empty-keywords-pause-write-path/decision.md`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md`;
  empty-keywords / mode-defaults / CH — не закрывают этот gap)
- [x] relevant decisions cited (ортогональность empty-keywords; Hold freeze≠stop)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision (`run_bidder_process_for_adv` Auto
  `update_cpm` gated by `auto_shelf_bid_control_enabled`; Search ветка без
  изменений; `/opsx-apply` 2026-08-11)
- [x] promoted to registry Accepted on archive 2026-08-11
