## 1. Tests-first: characterization и парные сценарии

- [x] 1.1 Найти runtime-seams записи ставки Авто для пути **«Управление ставкой для Авто»** (`bidder_for_auto`) и для **«Управление ставкой в полках»** (`auto_shelf_bid_control_enabled` → set_bid); зафиксировать в комментарии/докстринге теста, какой seam проверяем (spec `auto-bid-module-coexistence`).
- [x] 1.2 Добавить characterization/unit тест(ы): при **включённом** «Управление ставкой в полках» и включённом «Управление ставкой для Авто» — путь «для Авто» MUST NOT успешно изменить ставку Авто (до write boundary, не только `assert_not_called` финального мока без доказательства фильтрации). Docstring на русском со ссылкой на Scenario: Shelf bid control on — legacy Auto bid path ignored.
- [x] 1.3 Добавить paired positive unit тест: при **выключенном** «Управление ставкой в полках» и включённом «Управление ставкой для Авто» — старый путь MAY успешно идти к записи ставки Авто; путь полок MUST NOT писать. Docstring → Scenario: Shelf bid control off — legacy Auto bid path may write / Positive case when shelf control is off.
- [x] 1.4 Добавить/уточнить тест: при включённых полках оба модуля MUST NOT одновременно успешно писать ставку Авто (Scenario: Both modules must not write Auto bid together when shelves on).
- [x] 1.5 Добавить smoke на различимость причин: действие/результат **«Управление ставкой в полках»** MUST NOT фиксироваться как единственный durable `cost_rule_failed`; cost-пауза activity-control остаётся отдельной причиной (Scenario: Shelf bid action is not labeled as cost_rule_failed / Cost pause remains a separate activity reason). Без смены формулы cost-rule.
- [x] 1.6 Прогнать новые тесты: ожидаемо красные, если runtime ещё нарушает ignore старого пути при полках вкл; зафиксировать результат (gap да/нет).

  **1.6 result (2026-08-10):** gap **да**. `poetry run pytest tests/unit/auto_bid_module_coexistence/` → 2 failed / 2 passed. RED: `test_shelf_on_legacy_auto_bid_path_must_not_update_auto_cpm`, `test_shelf_on_both_modules_must_not_both_write_auto_bid` (legacy всё ещё вызывает `update_cpm(333, …)` при `auto_shelf_bid_control_enabled=True`). GREEN: shelf-off legacy write + ControlReason ≠ `cost_rule_failed`.

## 2. Минимальный gate (только если gap подтверждена)

- [x] 2.1 Если 1.6 показал gap: добавить узкий skip/ignore на legacy пути записи ставки Авто при `auto_shelf_bid_control_enabled`, **до** WB bid write; не трогать Search/не-Авто ветки того же bidder шире необходимого; не переписывать plan_distance / selection полок. Обоснование в комментарии/docstring со ссылкой на spec Mutual exclusion.

  **Done:** `run_bidder_process_for_adv` — `bidder_for_auto and not shelf_bid_control_on` перед `update_cpm(auto_adv_id)`; Search ветка без изменений.
- [x] 2.2 Если gap не подтверждена: явно отметить в этом tasks-чеклисте «gate не нужен — runtime уже соответствует»; не добавлять мёртвый код.

  **N/A:** gap подтверждена в 1.6 → выполнен 2.1 (мёртвый «gate не нужен» не добавлялся).
- [x] 2.3 Убедиться, что regression из 1.2 падает при удалении intended ignore/guard (удалить guard временно в локальной проверке или эквивалент).

  **2.3 (2026-08-11):** временно убран `and not shelf_bid_control_on` → `test_shelf_on_legacy_auto_bid_path_must_not_update_auto_cpm` FAILED; guard восстановлен → 4 passed.

## 3. Закрытие DoD и границы scope

- [x] 3.1 Прогнать targeted unit-набор coexistence (новые + затронутые соседние bidder/shelf тесты при необходимости); все зелёные.

  **3.1:** `poetry run pytest tests/unit/auto_bid_module_coexistence/` → 4 passed.
- [x] 3.2 Сверить placement с `decisions/auto-bid-module-coexistence-write-path/decision.md`: gate/ignore только на bid-write ownership; не в mode-defaults / empty-keywords / Hold.

  **3.2:** gate только в legacy Auto `update_cpm` ветке `bidder_func.py`; mode-defaults / empty-keywords / Hold не трогались.
- [x] 3.3 Scope check HARD: в diff нет terminal shelf pause/retest, empty-keywords Search, billing, plan_distance rewrite, нового `cost_rule_failed` mask для shelf-exhausted.

  **3.3:** production diff = docstring + shelf gate на Auto write; tests + planning artifacts only.
- [x] 3.4 При необходимости обновить checklist в decision: implementation layer matches decision.

## Telegram UI / Message Safety

Не требуется: этот change не создаёт и не меняет Telegram message/caption/callback/keyboard текст.
