# Decision: auto-shelf-exhausted-pause-write-path

## Status

Proposed

## Context

Accepted decisions закрывают соседние контуры, но **не** ownership terminal
паузы Авто при исчерпании теста «Управление ставкой в полках»:

- `openspec/decisions/empty-keywords-pause-write-path/decision.md` —
  TARGET_ENTITY_OR_LEG=SEARCH; adapters auction; reason `empty_keywords`.
- `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md` —
  mutual exclusion writers ставки; forward-compat требует отдельный decision
  для terminal shelf pause и запрещает маскировку под ordinary
  `cost_rule_failed`.

Change `auto-shelf-exhausted-pause-retest` / INC-AUTO-SHELF-PAUSE-01 вводит
detect → durable block/reason → WB pause/start Auto → clear-our-block /
retest → notify. Competing placements (detect в activity-control; pause в
shelf manager; terminal как `cost_rule_failed`) — high-risk write-path:
нужен reusable ownership до implementation-ready. Сейчас в registry —
**Architecture Decision Missing** для этого path.

## Decision

Reusable write-path capability `auto-shelf-exhausted-pause`:

1. **TARGET_ENTITY_OR_LEG = AUTO** — pause и matching условный start для
   terminal shelf-exhausted применяются к ноге **Авто** (WB Auto), не к
   Search и не к обеим ногам «заодно».
2. **ALLOWED_ADAPTERS** — `pause_auto_campaign`; для старта Авто после
   снятия нашего блока (когда других blockers нет) — matching Auto start
   seam activity-control.
3. **FORBIDDEN_ADAPTERS** — `pause_auction_campaign` / Search pause для
   этой причины; fallback Search или BOTH legs Forbidden.
4. **Layer ownership**
   - **Shelf («Управление ставкой в полках»)** — detect terminal (эпоха
     исчерпана + нет проходных vs resolve CPO при gate модуль ON + «Best
     plan»); durable epoch / наш pause-block / intent; тик-пересчёт
     resolve; сигнал clear нашего блока (календарь / проходные на тике).
   - **Activity-control** — исполнение WB pause/start Авто; запись
     distinct Auto-lane reason; уважение приоритета budget / schedule /
     balance / emergency над стартом; **не** detect terminal math.
   - **Telegram setting / UX полок** — интервал суток (product default 7),
     notify (почему + какой resolve CPO + когда перетест), кнопка
     «Сбросить паузу» = clear только нашего блока.
5. **Distinct reason** — durable terminal reason MUST NOT быть единственным
   `empty_keywords`, schedule/budget, или ordinary `cost_rule_failed`.
6. **Clear-our-block** — кнопка / тик / календарь снимают только наш блок
   этой причины. MUST NOT форсить старт Авто, если другие блоки держат
   паузу. Новая эпоха теста — только когда Авто **реально** стартует после
   снятия нашего блока.
7. **Mid-cycle cost gate** — пока «Управление ставкой в полках» ON,
   activity-control MUST NOT ставить Авто на паузу по себестоимости
   mid-cycle (в т.ч. best CPO + факт > target → `cost_rule_failed`) как
   замену terminal path. При модуле OFF прежний cost path MAY оставаться.
8. **Module stays ON** — terminal pause MUST NOT выключать
   `auto_shelf_bid_control_enabled` / «Управление ставкой в полках».
9. **Orthogonal** — не владеет mutual-exclusion bid writers (coexistence);
   не владеет empty-keywords Search path; Hold freeze ≠ stop.

## Applies to

- Capability `auto-shelf-exhausted-pause`
- Detect/intent/epoch в контуре «Управление ставкой в полках»
- `AutoAdvActiveControlService` pause/start Авто и Auto-lane reasons
- Paid Telegram shelf settings (interval, notify, «Сбросить паузу»)
- Paired regression: terminal Auto effect; Search non-effect; no mid-cycle
  cost pause when module ON; clear-our-block without forced start

## Allowed

- Shelf detect terminal → durable наш блок + activity-control
  `pause_auto_campaign` + distinct Auto reason + notify
- Clear нашего блока по календарю / «Сбросить паузу» / проходным на тике;
  старт Авто только если нет других blockers
- New epoch coverage window после реального старта Авто
  (`date_from = max(now-7d, epoch_start)` или эквивалент)
- При модуле OFF — legacy cost-пауза activity-control как раньше

## Forbidden

- `pause_auction_campaign` / Search pause для shelf-exhausted
- Pause BOTH legs «заодно» без нового Owner decision
- Маскировка terminal под `empty_keywords` или sole `cost_rule_failed`
- Detect/epoch math внутри Telegram handlers как единственный SoT
- WB pause внутри shelf bid setter «заодно» в обход activity-control
- Forced Auto start при clear нашего блока, пока живы другие blockers
- Выключение «Управление ставкой в полках» вместо паузы WB Auto
- Mid-cycle `cost_rule_failed` pause Авто при модуле ON как substitute
  terminal shelf-exhausted
- Класть ownership только в chat/design без decision+spec

## Examples

Good:

- Модуль ON + «Best plan», эпоха исчерпана, нет проходных vs resolve CPO →
  `pause_auto_campaign` + distinct reason; Search не паузится этим path
- «Сбросить паузу» при живом budget/schedule blocker → наш блок снят,
  Авто остаётся на паузе; эпоха ещё не стартовала
- Модуль ON → mid-cycle best+факт > target → Automust NOT pause via
  `cost_rule_failed`; terminal path остаётся отдельным

Bad:

- Terminal записан только как `cost_rule_failed`
- Clear нашего блока всегда вызывает start Auto несмотря на schedule
- Empty-keywords path паузит Авто «для полок»
- Detect terminal живёт только в Telegram callback без shelf/activity layers

## Related specs

- Change delta: `openspec/changes/auto-shelf-exhausted-pause-retest/specs/auto-shelf-exhausted-pause/spec.md` (после создания)
- Ортогонально: `openspec/specs/auto-bid-module-coexistence/spec.md`
- Ортогонально: `openspec/specs/pause-on-empty-keywords/spec.md`

## Related changes

- `openspec/changes/auto-shelf-exhausted-pause-retest` (introduced)
- Evolution: `openspec/evolution/affordable-auto-pause-on-empty.md`
  (`INC-AUTO-SHELF-PAUSE-01`)
- Cite Accepted:
  `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md`
  `openspec/decisions/empty-keywords-pause-write-path/decision.md`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md`;
  empty-keywords / coexistence не закрывают terminal Auto shelf path)
- [x] relevant decisions cited (ортогональность + forward-compat coexistence)
- [x] new decision proposed because accepted decision was missing
- [ ] implementation layer matches decision (после `/opsx-apply`)

## Semantic write target (durable)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: shelf-exhausted Auto pause / retest / clear-our-block
TARGET_ENTITY_OR_LEG: AUTO
ALLOWED_ADAPTERS: pause_auto_campaign; matching Auto start when no higher-priority blockers
FORBIDDEN_ADAPTERS: pause_auction_campaign (for this reason); BOTH-legs pause; sole cost_rule_failed as terminal mask
OWNER_DECISION_SOURCE: EVOLUTION_HANDOFF INC-AUTO-SHELF-PAUSE-01 + owner-contract + this Proposed decision
REQUIRED_PAIRED_TESTS: Auto paused for terminal; Search NOT paused by this path; clear-our-block without forced start; no mid-cycle cost pause when shelf module ON
```
