# Decision: architecture-decision-lookup (harden-ab-hold-confirmation-boundaries)

## Status

Proposed

## Context

Change усиливает access gate и валидацию confirmed target places в существующем
paid Telegram A/B Hold flow. Placement затрагивает ownership проверки в handlers,
candidate filtering в lifecycle helper и финальную защиту payload в epoch
write-path.

Context-first lookup выполнен по `design.md` § Architecture Decision References
и `openspec/decisions/index.md`. Новый reusable write-path или lifecycle owner
не требуется: change применяет уже принятые решения без смены durable SoT или
слоя записи.

## Decision

**Не создавать новый reusable architecture decision для archive.**

Размещение и инварианты полностью покрыты принятыми decisions:

1. `openspec/decisions/card-ab-hold-write-path-ownership/decision.md` —
   Telegram handlers как UI entrypoint; durable writes только через A/B Hold
   epoch/setup write-path; запрет обходных writers.
2. `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
   — PG lifecycle, `FOR UPDATE`, порядок PENDING intent → WB sync.
3. `openspec/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md` —
   confirmed target places как durable PG SoT; factual position — live read-model.

Telegram actor/access gate (`get_wb_user_cabinet_for_adv_and_telegram`) —
access control существующего paid UI write-path, не новый ownership layer.

## Applies to

- `card_ab_hold/telegram/*` handlers (actor gate, stale gate, UX surfaces)
- `card_ab_hold/epoch_write.py` (durable payload guard)
- W3 candidate validator / `_tp_rows_from_adv` read boundary

## Allowed

- Handlers проверяют actor → cabinet linkage до stale-check и PG mutation.
- Epoch write-path отклоняет invalid `tp_map` до `UPDATE`/`COMMIT`.
- Чистый validator исключает non-finite/non-positive factual positions до UI confirm.

## Forbidden

- Новый durable ACL или owner id в `callback_data`.
- FSM draft / callback payload как источник ownership.
- PG/Redis lifecycle writes из foreign callback после failed gate.
- Implicit zero target place fallback.

## Examples

**Good:** `disable_card_ab_hold_in_session(..., telegram_user_id=actor)` вызывает
`get_wb_user_cabinet_for_adv_and_telegram`; при `None` — reject без commit.

**Bad:** `telegram_user_id is not None and hasattr(adv, "wb_cabinet_id")` —
fail-open skip ownership на test doubles без `wb_cabinet_id`.

## Related specs

- `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md`

## Related changes

- `harden-ab-hold-confirmation-boundaries`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing — **нет; lookup закрыт без нового ADL**
- [x] implementation layer matches decision
