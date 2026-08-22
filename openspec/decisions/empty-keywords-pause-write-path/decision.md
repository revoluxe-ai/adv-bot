# Decision: empty-keywords-pause-write-path

## Status

Accepted

## Context

Prior accepted decision фиксировал ownership lifecycle empty-keywords
(detect → intent → activity-control pause/start → reason → recheck → notify;
≤7d; Hold orthogonality). INC-PAUSE-01 реализовал pause через **Auto**
adapter `pause_auto_campaign`.

Owner INC-PAUSE-02: для reason empty-keywords целевая нога — **Search**;
`pause_auto_campaign` для этой причины запрещён. Competing adapters в runtime
(`pause_auto_campaign` vs `pause_auction_campaign`) делают выбор ноги
high-risk semantic write target: chat-only ответ недостаточен — leg + adapters
MUST быть durable в registry decision.

Этот Accepted artifact — amendment того же decision slug: ownership слоёв
сохраняется; уточняется TARGET_ENTITY_OR_LEG и adapter matrix
(промоут из `retarget-empty-keywords-pause-to-search`, 2026-08-11).

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
6. **Settled-empty only (warmup ROOT-001):** empty-keywords intent arm и Search
   pause для этой причины MUST опираться на **settled empty** — bot-driven
   confirmed empty после keyword OFF (V3 intent) или эквивалентный durable
   settled-empty сигнал / recheck после уже settled empty-keywords pause.
   Redis warmup-маркер `__empty__` и transient zero-active keyword read,
   пока snapshot warmup ещё может populate keywords, MUST NOT считаться
   settled empty и MUST NOT вооружать no-prior-intent arm /
   `pause_auction_campaign`. Warmup false-empty ≠ bot-driven settled empty.
7. **User notify — all shop-linked recipients (notify-fanout ROOT-001 /
   Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`):** paid Telegram UX при
   входе в empty-keywords pause MUST уведомить **всех** пользователей,
   связанных с магазином через `WBUserCabinet` с non-null
   `user.user_telegram_id` (resolution =
   `get_wb_user_cabinets_for_shop` / `load_telegram_chat_ids_for_shop`;
   align token NotificationManager «all users of a shop»). MUST NOT
   ограничивать доставку одним primary recipient при нескольких chat_id.
   Debounce once-per-enter: attempt all; KEEP debounce if any delivery
   succeeds; RELEASE if none delivered. Support link — `const.SUPPORT_LINK`.
8. **User notify — resume/re-enable after pause episode (no-resume-notify
   ROOT-001 / SPEC_GAP):** после **доставленного** empty-keywords pause
   notify, когда Search/keywords resume или re-enable после этого pause
   episode, paid Telegram UX MUST отправить **отдельный** resume/re-enable
   notify тем же shop-linked recipients (clause 7 scope). Resume notify
   MUST быть distinct от pause-entry notify и от recheck-mention внутри
   pause message; pause-entry / recheck-mention MUST NOT замещать resume
   notify. Ordinary Search start без prior delivered pause-notify episode
   MUST NOT слать resume notify «за эту причину». Placement: notify emit
   seam (sibling of pause notify), не redesign pause write-path / adapters.
9. **Two-tick empty confirmation before Search pause (puna-empty-shape
   ROOT-001 / Owner `D_TWO_TICK_EMPTY_CONFIRMATION` /
   `TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`):** для no-prior-intent
   settled-empty confirmation lifecycle:
   - **Tick1** empty active keywords + Search STARTED → MUST
     record/latch only; MUST NOT `pause_auction_campaign` / MUST NOT
     pause Search в этом тике.
   - **Tick2** still empty → THEN pause Search
     (`pause_auction_campaign` + Search-lane `empty_keywords`).
   - **Later tick** keywords present → start/resume Search path MUST
     быть доступен (существующий recheck/resume может остаться).
   - **Ticks continue** across latch → pause → resume lifecycle.
   Warmup Redis `__empty__` остаётся non-settled (clause 6 / D8) и
   MUST NOT считаться tick1 settled confirmation. Two-tick latch — Owner
   settled-empty confirmation path когда нет prior V3 bot-driven intent.
   Same-tick arm+pause на первом empty observe — Forbidden.

## Applies to

- Capability `pause-on-empty-keywords`
- `AutoAdvActiveControlService` empty-keywords pause/recheck seam
- WB modifiers: `pause_auction_campaign` / Search start; not Auto pause for
  this reason
- Redis campaign activity reason (Search lane) + empty-keywords intent
- Paid Telegram notify about this pause reason **and** resume/re-enable
  after a delivered pause-notify episode
- Paired regression tests for Search effect / Auto non-effect / wrong adapter
- Paired regression tests for resume/re-enable notify after pause notify

## Allowed

- Consume empty-keywords intent → `pause_auction_campaign` when Search started
- Set Search-lane reason `empty_keywords` + notify **all** shop-linked
  Telegram recipients (debounce once-per-enter; any-success KEEP)
- Recheck/resume: Search start на той же ноге, когда нет более приоритетного
  Search pause reason; при снова пустом наборе ключей — снова Search pause
  с тем же reason
- After delivered pause notify + Search/keywords resume/re-enable → emit
  distinct resume/re-enable notify to same shop-linked recipients
- Keep V3 detect / Redis intent / 7d / Hold orthogonality
- Guard no-prior-intent arm against Redis `__empty__` / warmup false-empty
  (require settled-empty confirmation)
- No-prior-intent two-tick latch: tick1 empty → record/latch only; tick2
  still empty → `pause_auction_campaign`; later non-empty → Search
  start/resume; ticks continue (Owner
  `TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`)

## Forbidden

- `pause_auto_campaign` из empty-keywords path / for EMPTY_KEYWORDS
- Pause BOTH legs «заодно» без нового Owner decision
- Fallback: нет Search → паузить Auto
- Recheck, который стартует только Auto, оставляя Search на паузе «за эту
  причину»
- Маскировка reason под schedule/budget/cost
- Класть leg-выбор только в chat / design без decision+spec
- Arm empty-keywords intent / `pause_auction_campaign` на Redis `__empty__`
  warmup marker или transient `active_count==0` без settled-empty
  confirmation (no-prior-intent false pause during snapshot warmup)
- Notify only one primary shop-linked Telegram user when several
  `WBUserCabinet` rows expose distinct non-null `user_telegram_id`
  (Owner requires all-recipients)
- Omit resume/re-enable notify after delivered empty-keywords pause notify
  when Search/keywords resume (treating pause-entry or recheck-mention as
  sufficient)
- Emit empty-keywords resume notify on ordinary Search start without a
  prior delivered pause-notify episode
- Same-tick arm + `pause_auction_campaign` on first empty observe for
  no-prior-intent (skipping two-tick confirmation latch)
- Treating Redis warmup `__empty__` as tick1 settled confirmation

## Examples

Good:
- Intent consumed → `pause_auction_campaign(adv)` + Search reason
  `empty_keywords`; `pause_auto_campaign` not awaited
- Recheck: `start_auction_campaign` (или Search start seam) → V3 tick → empty
  → снова Search pause
- Search STARTED + Redis `__empty__` / warmup `[]` + no prior V3 intent →
  no arm, no Search pause (wait for settled empty or keyword populate)
- Two shop-linked telegram chat_ids → `send_message` twice (once each)
  after empty-keywords Search pause enter
- Delivered pause notify → Search resume / keywords re-enable → distinct
  resume `send_message` to each shop-linked chat_id
- Tick1 empty + Search STARTED + no prior V3 intent → latch/record only,
  no `pause_auction_campaign`; tick2 still empty → Search pause; later
  keywords → Search start/resume; ticks continue

Bad:
- `_maybe_pause_for_empty_keywords_intent` вызывает `pause_auto_campaign`
- Search paused for empty-keywords, recheck starts only Auto
- Missing Search leg → silent Auto pause fallback
- No-prior-intent arm treats `__empty__` as settled empty → premature
  `pause_auction_campaign` while warmup still loading keywords
- Empty-keywords notify hardcodes a single chat_id / primary owner when
  multiple shop-linked telegram ids exist
- Pause notify delivered, Search resumes, no resume/re-enable notify
- Resume notify text identical to pause-entry / only recheck-mention
- First empty observe (no prior intent) immediately calls
  `pause_auction_campaign` without a second confirming empty tick

## Related specs

- `openspec/specs/pause-on-empty-keywords/spec.md`

## Related changes

- `openspec/changes/archive/2026-08-11-retarget-empty-keywords-pause-to-search`
- Prior: `openspec/changes/archive/2026-08-08-pause-auto-campaign-on-empty-keywords`
- Supersedes leg/adapter placement of pre-INC-PAUSE-02 Accepted text
  (ownership layers unchanged; TARGET_ENTITY_OR_LEG=SEARCH)

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
OWNER_DECISION_SOURCE: EVOLUTION_HANDOFF INC-PAUSE-02 + this Accepted decision
REQUIRED_PAIRED_TESTS: Search paused; Auto NOT paused by this path; wrong-adapter regression on pause_auto_campaign
```
