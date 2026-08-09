## Context

INC-PAUSE-01 (`pause-auto-campaign-on-empty-keywords`) доставил lifecycle
empty-keywords: V3 post-OFF Redis intent →
`AutoAdvActiveControlService._maybe_pause_for_empty_keywords_intent` →
`pause_auto_campaign` + `AutoReasonCode.EMPTY_KEYWORDS` + notify; recheck =
обычный Auto start при PAUSE без нового intent.

Owner INC-PAUSE-02 (EVOLUTION_HANDOFF): целевая нога — **Search**;
ALLOWED `pause_auction_campaign`; FORBIDDEN `pause_auto_campaign` для этой
причины. Competing adapters уже в `WBModifier` / activity-control. Main spec и
accepted ADL описывают «кампанию», но не фиксируют ногу — нужно durable
amendment.

Стек: Python 3.11, shop-runner, Redis intent/reason, Search/Auto pause-start
seams, paid Telegram notify. Linked star
`affordable-auto-pause-on-empty` / `INC-PAUSE-02`.

## Goals / Non-Goals

**Goals:**

- Retarget empty-keywords pause write на Search (`pause_auction_campaign`).
- Recheck/resume той же Search-ноги (не оставлять Search paused, стартуя
  только Auto «за эту причину»).
- Forbid Auto adapter для EMPTY_KEYWORDS; no Auto fallback if Search missing.
- Durable SEMANTIC_WRITE_TARGET в decision + delta spec + paired tests.
- Сохранить reason `empty_keywords`, intent latch, notify, 7d invariants.

**Non-Goals:**

- Fair billing Auto/Search (`INC-BILL-LEG-PAUSE-01`), тариф 1000₽, disconnect
  UX, comms, onboard/free.
- Pause BOTH legs / keep Auto pause.
- Keyword selection / bids / minus / whitelist beyond empty-set hook.
- Process SEMANTIC_WRITE_TARGET meta-fix; retire v2.

## Architecture Decision References

- `openspec/decisions/empty-keywords-pause-write-path/decision.md` (Accepted) —
  ownership detect → intent → activity-control → reason/recheck/notify; ≤7d;
  Hold orthogonality. **Incomplete for leg/adapters** → amendment required.
- `openspec/changes/retarget-empty-keywords-pause-to-search/decisions/empty-keywords-pause-write-path/decision.md`
  (Proposed) — TARGET_ENTITY_OR_LEG=SEARCH; ALLOWED/FORBIDDEN adapters.
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` (Accepted) —
  defaults overlays не трогаем.
- Coexistence: A/B Hold freeze ≠ stop (card-ab-hold) — без изменений.

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|---|---|---|
| Detect empty after bot OFF | auto-updater v3 apply hook (unchanged) | Telegram; billing |
| Empty-keywords pause WB write | activity-control → `pause_auction_campaign` | `pause_auto_campaign` for this reason; BOTH-legs |
| Recheck/resume WB write | activity-control Search start seam | Auto-only start «за empty-keywords» |
| Reason durability | Search activity-reason lane, code `empty_keywords` | Mask as schedule/budget/cost; Auto-lane as sole pause target for this path |
| Intent latch | Redis empty-keywords intent (komplekt / auto adv id key ok) | Mode-defaults overlays |
| Notify | existing paid Telegram path | Channel/marketing copy |

Placement MUST match proposed amended `empty-keywords-pause-write-path`.

## Semantic write target

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: empty-keywords pause / recheck
TARGET_ENTITY_OR_LEG: SEARCH
ALLOWED_ADAPTERS: pause_auction_campaign; matching Search start for recheck/resume
FORBIDDEN_ADAPTERS: pause_auto_campaign (for EMPTY_KEYWORDS)
TARGET_EVIDENCE: Owner INC-PAUSE-02 handoff; runtime competing adapters; current path uses pause_auto_campaign
OWNER_DECISION_SOURCE: EVOLUTION_HANDOFF + proposed decision + this design + delta spec
REQUIRED_PAIRED_TESTS: Search paused; Auto NOT paused by empty-keywords path; wrong-adapter regression fails if pause_auto_campaign used
```

## Decisions

### D1. Pause adapter = Search only

**Выбор:** empty-keywords path вызывает `pause_auction_campaign` для
`ComplexAdv` с Search-ногой. `pause_auto_campaign` из этого path — Forbidden.

**Если `search_adv_id` отсутствует:** MUST NOT fallback на Auto pause; log +
skip pause write (intent consume policy: не оставлять бесконечный retry-storm —
зафиксировать в apply: consume + no Auto pause, или leave intent только если
есть безопасный retry; предпочесть consume + structured skip log, чтобы не
бить Auto).

**Альтернативы:** (a) BOTH legs — отвергнуто Owner; (b) keep Auto — отвергнуто
INC-PAUSE-02.

### D2. Reason lane = Search; code string unchanged

**Выбор:** писать reason `empty_keywords` на Search activity-reason lane
(`_set_search_reason` / эквивалент). Добавить
`AuctionReasonCode.EMPTY_KEYWORDS = "empty_keywords"` (тот же string value, как
у Auto enum — keep existing reason code). Display «Нет акт ключей» остаётся /
мапится на тот же value. Auto-lane MUST NOT получать EMPTY_KEYWORDS от этого
path.

**Альтернативы:** оставить reason только на Auto-lane при Search pause —
Forbidden (нога и reason разъедутся).

### D3. Where to consume intent

**Выбор:** сохранить consume в activity-control после schedule/budget/cost
гейтов комплекта (как сейчас «следующий шаг»), но исполнение pause — Search
adapter. Практично: вызывать из текущего auto-handler seam **или** перенести
в search-handler при том же ordering invariant (после OFF, не concurrent).
Prefer minimal move: заменить adapter/reason в существующем
`_maybe_pause_for_empty_keywords_intent` (+ rename/doc если нужно), при этом
статус/pause condition читать по **Search** active status.

**Альтернативы:** дублировать pause в обоих handlers — Forbidden.

### D4. Recheck/resume same Search leg

**Выбор:** пока Search на паузе по empty-keywords и нет более приоритетного
Search blocker, recheck MUST использовать Search start
(`start_auction_campaign` / `_start_auction_campaign_maybe_retry`). MUST NOT
считать «recheck выполнен», если стартовала только Auto, а Search остался
paused из-за empty-keywords.

Текущий Auto resume при PAUSE без intent остаётся для **Auto** budget/cost
lifecycle и не является empty-keywords recheck для Search.

Нужен явный Search-side gate: empty-keywords reason на Search + отсутствие
intent не блокирует периодический Search start (аналог нынешнего Auto
recheck test), а после start при снова empty — V3 снова ставит intent →
Search pause.

### D5. Migration of already-paused Auto from INC-PAUSE-01

**Выбор:** при первом проходе empty-keywords path / ensure: если Auto reason
lane ещё `empty_keywords` от старого поведения — clear/overwrite Auto reason
обычной Auto логикой (budget/cost), **не** держать Auto на паузе «ради»
empty-keywords. Не делать массовый one-shot migrator вне shop-runner tick,
если tick достаточно сходит.

### D6. Paired tests (required)

1. Intent → Search paused (`pause_auction_campaign` awaited); reason Search
   lane `empty_keywords`; notify once.
2. Same path: `pause_auto_campaign` **not** awaited.
3. Wrong-adapter regression: assertion / test fails if implementation calls
   `pause_auto_campaign` for empty-keywords.
4. Recheck: Search start when Search paused for empty-keywords without new
   blocking intent/higher priority; Auto-only start insufficient.
5. Keep: reason ≠ schedule/budget; 7d gate; Hold not forced OFF.

### D7. Notify / UX

**Выбор:** переиспользовать существующий notify text (причина + перепроверка);
при необходимости уточнить, что на паузе Search-нога — только если copy уже
говорит «кампания» двусмысленно; не раздувать в канал-анонс (out of scope).

## Risks / Trade-offs

- [Auto остаётся STARTED при пустых ключах] → осознанный Owner trade-off
  INC-PAUSE-02; billing fair-pause — отдельный increment.
- [Нет Search-ноги] → skip, no Auto fallback; мониторить skip logs.
- [Recheck стартует Auto, Search забыт] → paired test D6.4; Search reason gate.
- [Старые Auto EMPTY_KEYWORDS в Redis] → D5 clear via ordinary Auto path.
- [parse_reason_code предпочитает Auto enum при shared value] → уже паттерн
  для common codes; display по string value; tests на value `empty_keywords`.

## Migration Plan

1. Ship code: Search pause/recheck + AuctionReasonCode.EMPTY_KEYWORDS + tests.
2. Promote decision at archive; sync main spec from delta.
3. Rollback: revert to Auto adapter only with **new** Owner decision (не
   silent); emergency — disable empty-keywords intent consume.

## Open Questions

- (none blocking) Точный prefer: consume в auto-handler vs search-handler —
  apply выбирает минимальный diff при соблюдении D1–D4.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (leg/adapter amendment)
- [x] implementation layer matches decision
