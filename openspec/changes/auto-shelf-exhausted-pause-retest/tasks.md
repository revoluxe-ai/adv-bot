## TASK_GENERATION_READINESS

```text
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes
TASKS_STATUS: READY
REASON: none
```

Upstream: design `DESIGN_STATUS: READY` (body: Durable SoT PG
`AutoShelfBidControlState`/`Settings` + Redis Auto-lane reason mirror only;
`DESIGN_READINESS` block present); spec `auto-shelf-exhausted-pause`
(18 scenarios); proposed decision `auto-shelf-exhausted-pause-write-path`
(`DURABLE_SOT_STATUS: RESOLVED`); owner-contract L1–L6.

Evidence roles: `LEGACY_BASELINE` = mid-cycle cost pause **before** kill when
shelf ON; `TARGET_REGRESSION` / `FINAL_ACCEPTANCE` = new shelf-exhausted
lifecycle. Не требовать, чтобы LEGACY mid-cycle cost assertions оставались
зелёными после intentional change при module ON.

## 1. Tests-first / scenario matrix (до production)

- [ ] 1.1 `LEGACY_BASELINE`: characterization mid-cycle cost pause Авто через
  activity-control при `auto_shelf_bid_control_enabled` ON (ветка best CPO +
  факт > target → `cost_rule_failed`) — зафиксировать текущее поведение до
  kill (spec «No mid-cycle cost pause while shelf module is on»).
- [ ] 1.2 `TARGET_REGRESSION` gate OFF: module OFF → MUST NOT shelf-exhausted
  Auto pause (Scenario: Module off — no shelf-exhausted pause).
- [ ] 1.3 `TARGET_REGRESSION` gate non–Best plan: shelves ON + не «Best plan»
  → MUST NOT terminal path (Scenario: Non-Best plan mode — no shelf-exhausted
  pause).
- [ ] 1.4 `TARGET_REGRESSION` terminal pause: exhausted + no resolve-CPO fit →
  `pause_auto_campaign` + module stays ON; SIDE_EFFECT_PROOF this-run
  (Scenario: Exhausted epoch… / Already-exhausted on reconcile tick…).
- [ ] 1.5 Paired forbidden Search: тот же path MUST NOT `pause_auction_campaign`
  (Scenario: Search leg not paused by shelf-exhausted); тест MUST падать при
  удалении forbid.
- [ ] 1.6 Negative: still have bids to test → MUST NOT terminal pause
  (Scenario: Still have bids to test — no terminal pause).
- [ ] 1.7 Distinct reason + recorded resolve CPO kind/value; MUST NOT sole
  `cost_rule_failed` / empty-keywords / schedule / budget
  (Scenarios: Reason is not masked…; Resolve CPO used for terminal is visible).
- [ ] 1.8 Clear-our-block without forced start: calendar due / «Сбросить
  паузу» / pass points on tick — при другом blocker MUST clear only our PG
  block AND MUST NOT force Auto start (Scenarios: Calendar due…; Reset pause
  button…; Pass points on tick…).
- [ ] 1.9 Keep-block: no fit on tick + interval not due → our block MUST
  persist (Scenario: No fit on tick keeps our pause block).
- [ ] 1.10 Conditional start + new epoch: only our block → Auto MAY start;
  epoch + coverage `date_from = max(now-7d, epoch_start)` only on **real**
  Auto start (Scenario: Auto starts and new epoch…).
- [ ] 1.11 Default interval 7 days (Scenario: Default interval is seven days).
- [ ] 1.12 Mid-cycle cost: module ON → MUST NOT ordinary cost Auto pause
  mid-cycle; module OFF → MAY legacy cost pause (Scenarios: Shelf module on…
  / Shelf module off…). `FINAL_ACCEPTANCE` после kill ветки.
- [ ] 1.13 Coexistence smoke: shelves ON → legacy Auto bid MUST NOT succeed
  (Scenario: Shelves on — legacy Auto bid path still ignored); не rewrite
  coexistence gate.
- [ ] 1.14 Stub contracts: scenario_seam stubs для `pause_auto_campaign` /
  Auto start / Telegram send MUST иметь ContractCase / shared shape parity
  с boundary (или явный TEST_DEBT → `/opsx-test`); Redis fakeredis OK для
  reason mirror; PG write/read boundaries отдельно если SoT assertions
  зависят от persistence.

## 2. Durable SoT — PG migration + shelf state

- [ ] 2.1 Миграция PG: `AutoShelfBidControlSettings` — interval days
  (product default 7); `AutoShelfBidControlState` — our-block flag/timestamps,
  epoch_start, recorded resolve CPO kind/value, due-retest; exact column
  names = harmless naming из design Open Questions.
- [ ] 2.2 Repository read/write seams: shelf owns PG SoT; session
  `read_only=` explicit; parent→child session handoff где применимо.
- [ ] 2.3 Recovery: после «рестарта» (новый process / cold read) our-block
  читается из PG; Redis reason MAY re-assert из PG — тест на persist block.

## 3. Shelf detect / latch / clear (L2, L5)

- [ ] 3.1 Gate runtime: `auto_shelf_bid_control_enabled` + strategy
  «Best plan» (`plan_distance`); иначе path no-op.
- [ ] 3.2 Terminal detect на тике: нет next bid по мин. шагу в эпохе AND нет
  qualified-tested под **текущий resolve CPO** (цель vs макс — не «всегда
  Max») → latch PG our-block + record resolve CPO.
- [ ] 3.3 Already-true reconcile: условие уже true до тика → тот же arm на
  periodic tick (steady-state Scenario).
- [ ] 3.4 While paused: тик пересчёт resolve; fit → clear only our PG block;
  no fit → keep block; calendar due → clear only our block.
- [ ] 3.5 Новая эпоха + coverage clamp только после реального Auto start
  (не на clear alone).

## 4. Activity-control pause / start / mid-cycle (L1, L3, L6)

- [ ] 4.1 На terminal signal: `pause_auto_campaign` + Redis Auto-lane
  distinct reason (design-default `shelf_exhausted_no_plan`); MUST NOT
  Search pause; модуль полок MUST остаться ON.
- [ ] 4.2 Mid-cycle: при shelf module ON MUST NOT ветка best CPO+факт →
  `cost_rule_failed` pause Automid-cycle; при OFF — legacy MAY.
- [ ] 4.3 Clear our block + no other blockers → matching Auto start MAY;
  при чужих blockers MUST NOT forced start.
- [ ] 4.4 Recovery re-assert Redis reason from PG when block still set.

## 5. Telegram UX / notify (L4)

- [ ] 5.1 Setting interval days (default 7) в UI полок; persist PG settings.
- [ ] 5.2 Paid notify при enter pause: почему, какой resolve CPO, когда
  перетест; кнопка «Сбросить паузу» → clear only our PG block; Free MUST NOT
  получать write/notify path.
- [ ] 5.3 Fanout shop-linked — следовать существующему paid notify pattern
  (как empty-keywords), без redesign биллинга.

## Telegram UI / Message Safety

- [ ] T1 Identify every changed Telegram payload surface (notify + кнопка +
  interval setting copy).
- [ ] T2 Add/update tests with worst-case dynamic placeholder data (CPO
  values, dates, shop names).
- [ ] T3 Assert Telegram Bot API limits from
  `openspec/policies/telegram_bot_api_limits.md`.
- [ ] T4 Assert valid parse_mode / escaping.
- [ ] T5 Assert callback_data length in UTF-8 bytes («Сбросить паузу»).
- [ ] T6 Assert no raw technical text leaks (`pause_auto_campaign`,
  enum names в сыром виде).

## 6. Границы change / verification prep

- [ ] 6.1 Targeted unit (+ нужные integration) по matrix §1; не full suite
  без нужды.
- [ ] 6.2 Placement vs proposed decision: shelf detect/PG SoT;
  activity-control WB+Redis mirror; Telegram clear signal only.
- [ ] 6.3 Scope HARD: нет billing/1000₽/comms/empty-keywords Search rewrite /
  coexistence rewrite / BOTH-legs / выключение модуля вместо pause Auto /
  plan_distance math rewrite.
- [ ] 6.4 После apply: `/opsx-verify mode=impl` затем scenario coverage
  audit; archive только после PA + coverage certify/audit PASS.
