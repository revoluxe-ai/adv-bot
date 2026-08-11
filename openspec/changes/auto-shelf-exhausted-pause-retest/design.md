## Context

Linked: `affordable-auto-pause-on-empty` / `INC-AUTO-SHELF-PAUSE-01`.
Coexistence writers ставки уже DONE; empty-keywords — Search-only.
Нужен terminal lifecycle Авто при «Управление ставкой в полках» + «Best plan»:
исчерпание эпохи теста без ставки под resolve CPO → pause Auto; clear только
нашего блока; выпил mid-cycle cost-паузы при модуле ON.

Стек: Python 3.11; `AutoShelfBidControlManager` (coverage / qualified /
plan_distance / resolve CPO); `AutoAdvActiveControlService` (pause/start,
`cost_rule_failed`); Redis Auto-lane reasons; PG settings/state полок;
paid Telegram UI полок. Паттерн слоёв — как empty-keywords, но TARGET=AUTO.

## Goals / Non-Goals

**Goals:**

- Detect terminal + durable наш pause-block/reason + recorded resolve CPO.
- WB `pause_auto_campaign` через activity-control; distinct Auto reason.
- Clear-our-block: календарь N суток (default 7) / «Сбросить паузу» / тик с
  проходными; старт Авто только без других blockers; эпоха при реальном старте;
  coverage `date_from = max(now-7d, epoch_start)` (или эквивалент).
- Выпилить mid-cycle cost pause при `auto_shelf_bid_control_enabled` ON.
- Telegram notify + interval setting + кнопка; Free MUST NOT получать write-path.
- Proposed ADL уже в change; design следует ему.

**Non-Goals:**

- Billing ног, 1000₽, comms, disconnect, onboard, retire v2.
- Empty-keywords Search; rewrite plan_distance/selection math.
- Pause Search / BOTH legs; выключение модуля полок вместо pause Auto.
- Terminal для CTR/CPC/иных main bid кроме «Best plan».

## Architecture Decision References

- `openspec/changes/auto-shelf-exhausted-pause-retest/decisions/auto-shelf-exhausted-pause-write-path/decision.md`
  (Proposed) — ownership shelf → activity-control → Telegram; TARGET=AUTO;
  clear-our-block; mid-cycle cost gate; SEMANTIC_WRITE_TARGET.
- `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md`
  (Accepted) — writers mutual exclusion; не маскировать terminal под
  `cost_rule_failed`; freeze≠stop.
- `openspec/decisions/empty-keywords-pause-write-path/decision.md`
  (Accepted) — ортогональный Search path; не копировать adapters.

## Ownership & Placement

| Layer | Owns | Must not own |
|-------|------|----------------|
| Shelf control | detect terminal; epoch / наш block; resolve recompute; clear signals (due / fit / button intent) | WB pause/start adapters; budget/schedule priority |
| Activity-control | `pause_auto_campaign` / Auto start; Auto-lane reason; respect higher-priority blockers; mid-cycle cost gate when shelf ON | terminal math / plan_distance |
| Telegram shelf UX | interval days (default 7); notify; «Сбросить паузу» → clear нашего блока | detect SoT; forced start |

**Forbidden layers:** V3 keyword empty-keywords path; legacy `bidder_for_auto`
writer; mode-defaults overlays как SoT terminal; UI-only без runtime gate.

Rationale: тот же split detect→execute, что empty-keywords, с другой ногой и
другим detect owner (shelf, не V3 keyword OFF).

## Product Acceptance

```text
PRODUCT_ACCEPTANCE_REQUIRED: true
SCENARIO_COVERAGE_REQUIRED: true
REASON: SEMANTIC_WRITE_TARGET (AUTO vs Search) + EVOLUTION_LINK INC-AUTO-SHELF-PAUSE-01
  + material Auto pause/start + paid Telegram notify lifecycle
```

## OWNER_LIFECYCLE_ECHO

Упорядоченный смысл во времени (owner-contract / INC-AUTO-SHELF-PAUSE-01):

1. **Gate observe.** Path жив только если «Управление ставкой в полках» ON и
   main bid «Best plan»; иначе no-op. Пока модуль ON, контроль активности
   MUST NOT mid-cycle паузить Авто ordinary cost (`cost_rule_failed` и т.п.)
   посреди теста; при модуле OFF прежняя cost-пауза MAY оставаться.
2. **Terminal detect / latch.** Эпоха теста исчерпана (нет next bid по мин.
   шагу) и среди квалифицированно протестированных нет ставки под **текущий
   resolve CPO** (цель, если прогноз закрывает план; иначе макс — не «всегда
   Max») → durable наш pause-block / intent.
3. **Auto pause write.** Activity-control паузит ногу **Авто** на WB
   (`pause_auto_campaign`); distinct Auto-lane reason (не empty-keywords /
   schedule / budget / sole `cost_rule_failed`); recorded resolve CPO
   kind+value; модуль полок остаётся ON; Search этим path MUST NOT паузиться.
4. **Notify.** Paid Telegram: почему пауза, какой CPO учли, когда календарный
   перетест; кнопка «Сбросить паузу». Free MUST NOT получать этот write/notify.
5. **While paused — clear-our-block.** Тик: пересчёт resolve CPO; проходные /
   календарь N суток (default 7) / «Сбросить паузу» снимают **только** наш
   блок. Чужие blockers (бюджет/расписание/баланс/авария) могут держать Авто
   на паузе — MUST NOT forced start.
6. **Условный старт + новая эпоха.** Авто стартует на WB только если после
   clear нашего блока больше нечему держать паузу. Новая эпоха теста и
   coverage `date_from = max(now-7d, epoch_start)` (или эквивалент) — только
   когда Авто **реально** стартует; clear alone при чужих blockers эпоху
   MUST NOT начинать.

`CONFIRM_LIFECYCLE`: **confirmed** (Owner, 2026-08-11) — echo accepted; PA
MEANING_LOCK + Owner lifecycle spirit locked; scenario coverage plan/audit
still required before archive verify GO.

## Lifecycle

```text
LIFECYCLE_STATUS: DERIVED
```

Планировочное представление того же spirit, что owner-contract + echo выше
(без новых product semantics):

**L1. Gate observe + mid-cycle cost gate**
SOURCE: owner-contract.md (Решения Owner: module + Best plan; mid-cycle kill
when shelves ON) / OWNER_LIFECYCLE_ECHO §1 / proposed decision mid-cycle gate

**L2. Terminal detect / latch**
SOURCE: owner-contract.md (исчерпание + нет ставки под resolve CPO) /
OWNER_LIFECYCLE_ECHO §2 / decision detect ownership = shelf

**L3. Auto pause write**
SOURCE: owner-contract.md (пауза Авто, модуль ON, Search не этим path) /
OWNER_LIFECYCLE_ECHO §3 / SEMANTIC_WRITE_TARGET AUTO + pause_auto_campaign

**L4. Notify**
SOURCE: owner-contract.md (почему / какой CPO / когда перетест / «Сбросить
паузу») / OWNER_LIFECYCLE_ECHO §4

**L5. While paused — clear-our-block / keep-block**
SOURCE: owner-contract.md (тик / календарь / кнопка; без forced start; тик
без проходных → блок сохраняется) / OWNER_LIFECYCLE_ECHO §5

**L6. Conditional Auto start + new epoch**
SOURCE: owner-contract.md (старт только без других blockers; эпоха при
реальном старте; coverage clamp) / OWNER_LIFECYCLE_ECHO §6

## Decisions

1. **Gate** — runtime: `auto_shelf_bid_control_enabled` + strategy «Best plan»
   (`plan_distance`). Иначе path no-op.
2. **Terminal predicate** — нет next test по мин. шагу в окне эпохи AND нет
   qualified-tested bid с expected CPO в пределах **текущего resolve CPO**
   (цель vs макс от плана/прогноза). Не «всегда Max».
3. **Durable SoT (resolved — not apply-time):**
   - **WHAT:** our pause-block; `epoch_start`; recorded resolve CPO
     kind/value; due-retest timestamps; retest interval days (default 7);
     Auto-lane activity reason for display/priority with other blockers.
   - **WHERE / WHO owns canonical state:**
     - **PG** `AutoShelfBidControlSettings` — interval days (product default
       7). Shelf settings SoT.
     - **PG** `AutoShelfBidControlState` — canonical our-block / epoch /
       recorded resolve CPO / due timestamps. Shelf owns this SoT; MUST
       survive worker restart.
     - **Redis** `RedisCampaignActivityReasonManager` Auto-lane — **mirror
       only** of the distinct activity reason (same pattern as
       empty-keywords / cost reasons). MUST NOT be the sole SoT of our
       pause-block.
   - **WHO may write:** shelf repository → PG block/epoch/resolve/interval;
     activity-control → Redis Auto reason + WB pause/start; Telegram →
     clear signal that clears PG our-block only (no forced start).
   - **HOW recover:** after worker restart, shelf reads PG; if our-block
     still set and Auto remains paused for this reason, activity-control
     MAY re-assert Redis Auto reason from PG.
4. **Reason** — новый Auto-lane code, distinct от `empty_keywords` /
   schedule / budget / sole `cost_rule_failed` (Redis mirror; PG holds
   recorded resolve CPO + block).
5. **Clear-our-block** — due interval / button / tick fit снимают только наш
   block. Activity-control MAY start Auto только если нет других blockers.
   Новая эпоха + coverage clamp — при реальном старте Авто после clear.
6. **Mid-cycle cost** — при shelf module ON ветка best CPO+факт →
   `cost_rule_failed` pause Automust NOT срабатывать; при OFF — legacy
   сохраняется. Альтернатива «оставить ортогональный cost» отвергнута Owner
   (конфликт с дотестом).
7. **Notify** — paid Telegram: почему, какой resolve CPO, когда перетест;
   кнопка «Сбросить паузу». Fanout shop-linked — следовать существующему
   paid notify pattern (как empty-keywords), без redesign биллинга.
8. **Coexistence** — не трогать gate «полки ON → legacy bid ignore».

**Alternatives considered:** terminal только через `cost_rule_failed` —
Forbidden (маскировка). Forced start на кнопку — отвергнуто Owner (другие
блоки). Detect в одном только activity-control — отвергнуто (shelf владеет
coverage/epoch).

## Risks / Trade-offs

- [Ложный terminal / ранний pause] → строгий gate Best plan + qualified +
  resolve; paired tests.
- [Форс-старт / вечная пауза] → clear-our-block tests с чужими blockers;
  start только через обычный activity priority.
- [Регресс cost при module OFF] → paired ON/OFF cost tests.
- [Эпоха «закрыта» старой историей] → `date_from = max(now-7d, epoch_start)`.
- [Telegram limits] → payload-limit tests на notify/кнопку.
- [High-risk WB writes] → узкий adapter surface; Free guard.

## Migration Plan

- Миграция PG при необходимости: interval days (default 7), durable block /
  epoch fields (минимальный набор).
- Rollout: feature на paid shelf-enabled; dry-run логов detect→intent до
  широкого pause, если риск высок.
- Rollback: отключить path / вернуть mid-cycle cost при module ON; снять
  terminal reason consumers. Coexistence и Search empty-keywords не откатывать.

## Validation plan

- Unit: terminal detect; resolve CPO kind/value recorded; clear-our-block
  without forced start; mid-cycle cost blocked when module ON / allowed when
  OFF; coexistence regression smoke.
- Activity: Auto paused; Search not paused by this path; wrong-adapter
  regression.
- Telegram payload limits (worst-case dynamic).
- Characterization перед правкой cost-ветки при module ON.

## Open Questions

Harmless naming only (authority/SoT fixed above):

- Exact Auto-lane reason string / enum (design-default:
  `shelf_exhausted_no_plan` — may rename without changing semantics).
- Exact PG column / migration names for block/epoch/resolve/due/interval
  fields.

## DESIGN_READINESS

```text
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
REASON: none
```

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`auto-shelf-exhausted-pause-write-path`)
- [x] implementation layer matches decision (shelf → activity-control → Telegram)
- [x] durable SoT / write authority / recovery resolved (not deferred to apply)
