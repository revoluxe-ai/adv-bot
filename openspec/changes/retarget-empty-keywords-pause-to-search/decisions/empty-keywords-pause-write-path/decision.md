# Decision: empty-keywords-pause-write-path

## Status

Proposed

## Context

Accepted decision
`openspec/decisions/empty-keywords-pause-write-path/decision.md` уже фиксирует
ownership lifecycle empty-keywords (detect → intent → activity-control
pause/start → reason → recheck → notify; ≤7d; Hold orthogonality). INC-PAUSE-01
реализовал pause через **Auto** adapter `pause_auto_campaign`.

Owner INC-PAUSE-02: для reason empty-keywords целевая нога — **Search**;
`pause_auto_campaign` для этой причины запрещён. Competing adapters в runtime
(`pause_auto_campaign` vs `pause_auction_campaign`) делают выбор ноги
high-risk semantic write target: chat-only ответ недостаточен — leg + adapters
MUST быть durable в registry decision.

Этот artifact — proposed amendment того же decision slug: ownership слоёв
сохраняется; уточняется TARGET_ENTITY_OR_LEG и adapter matrix.

## Decision

Reusable write-path capability `pause-on-empty-keywords` сохраняет ownership
из accepted decision (detect после bot OFF в V3; pause как следующий шаг в
activity-control; distinct reason; recheck; notify; ≤7d; Hold orthogonality).

Дополнительный invariant (INC-PAUSE-02):

1. **TARGET_ENTITY_OR_LEG = SEARCH** — pause и matching recheck/resume для
   reason empty-keywords применяются к **Search** (auction) ноге комплекта
   авто-настройки, не к Auto.
2. **ALLOWED_ADAPTERS** — `pause_auction_campaign`; для recheck/resume той же
   ноги — matching Search start (`start_auction_campaign` / существующий
   Search start seam activity-control).
3. **FORBIDDEN_ADAPTERS** — `pause_auto_campaign` для reason EMPTY_KEYWORDS /
   empty-keywords path. Запрещено «fallback на Auto», если Search-ноги нет.
4. Reason code string остаётся `empty_keywords` (не маскировать под
   schedule/budget/cost). Durable reason для этого эпизода пишется на
   **Search** activity-reason lane (не как оправдание паузы Auto этим path).
5. Detect/intent после V3 keyword OFF на автокампании может по-прежнему
   keyed на auto setting / auto adv id комплекта; **исполнение** pause/start
   для этого reason — только Search adapters.

При archive: promote поверх accepted decision (тот же slug) со Status Accepted.

## Applies to

- Capability `pause-on-empty-keywords`
- `AutoAdvActiveControlService` empty-keywords pause/recheck seam
- WB modifiers: `pause_auction_campaign` / Search start; not Auto pause for
  this reason
- Redis campaign activity reason (Search lane) + empty-keywords intent
- Paid Telegram notify about this pause reason
- Paired regression tests for Search effect / Auto non-effect / wrong adapter

## Allowed

- Consume empty-keywords intent → `pause_auction_campaign` when Search started
- Set Search-lane reason `empty_keywords` + notify (debounce unchanged)
- Recheck/resume: Search start на той же ноге, когда нет более приоритетного
  Search pause reason; при снова пустом наборе ключей — снова Search pause
  с тем же reason
- Keep V3 detect / Redis intent / 7d / Hold orthogonality / notify semantics

## Forbidden

- `pause_auto_campaign` из empty-keywords path / for EMPTY_KEYWORDS
- Pause BOTH legs «заодно» без нового Owner decision
- Fallback: нет Search → паузить Auto
- Recheck, который стартует только Auto, оставляя Search на паузе «за эту
  причину»
- Маскировка reason под schedule/budget/cost
- Класть leg-выбор только в chat / design без decision+spec

## Examples

Good:
- Intent consumed → `pause_auction_campaign(adv)` + Search reason
  `empty_keywords`; `pause_auto_campaign` not awaited
- Recheck: `start_auction_campaign` (или Search start seam) → V3 tick → empty
  → снова Search pause

Bad:
- `_maybe_pause_for_empty_keywords_intent` вызывает `pause_auto_campaign`
- Search paused for empty-keywords, recheck starts only Auto
- Missing Search leg → silent Auto pause fallback

## Related specs

- `openspec/specs/pause-on-empty-keywords/spec.md`
- `openspec/changes/retarget-empty-keywords-pause-to-search/specs/pause-on-empty-keywords/spec.md`

## Related changes

- Active: `openspec/changes/retarget-empty-keywords-pause-to-search`
- Prior: `openspec/changes/archive/2026-08-08-pause-auto-campaign-on-empty-keywords`
- Supersedes leg/adapter placement of accepted
  `openspec/decisions/empty-keywords-pause-write-path/decision.md` (ownership
  layers unchanged)

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
  (`empty-keywords-pause-write-path`; `mode-defaults-policy-ownership`)
- [x] new decision proposed because accepted decision was missing durable
  TARGET_ENTITY_OR_LEG / adapter matrix (amendment)
- [x] implementation layer matches decision
  (`_maybe_pause_for_empty_keywords_intent` → `pause_auction_campaign` +
  Search-lane `AuctionReasonCode.EMPTY_KEYWORDS`; no `pause_auto_campaign`;
  apply hook uses Search status for recheck intent)

## Semantic write target (durable)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: empty-keywords pause / recheck
TARGET_ENTITY_OR_LEG: SEARCH
ALLOWED_ADAPTERS: pause_auction_campaign; matching Search start for recheck/resume
FORBIDDEN_ADAPTERS: pause_auto_campaign (for EMPTY_KEYWORDS)
OWNER_DECISION_SOURCE: EVOLUTION_HANDOFF INC-PAUSE-02 + this proposed decision
REQUIRED_PAIRED_TESTS: Search paused; Auto NOT paused by this path; wrong-adapter regression on pause_auto_campaign
```
