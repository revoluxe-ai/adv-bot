## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: affordable-auto-pause-on-empty
INCREMENT_ID: INC-PAUSE-02
KEEP: Search-only empty-keywords pause/recheck + forbid Auto adapter; no billing/comms
HARD: EVOLUTION_SCOPE_DRIFT if artifacts/tasks include OUT_OF_SCOPE or FUTURE_INCREMENTS
```

## Why

INC-PAUSE-01 уже умеет empty-keywords pause, но write-path бьёт в **Auto**-ногу
(`pause_auto_campaign`). Owner зафиксировал: для причины empty-keywords целевая
нога — **Search** (`pause_auction_campaign`); пауза Auto по этому reason
запрещена. Нужно перенацелить pause/recheck на Search и сделать выбор
TARGET_ENTITY_OR_LEG=SEARCH durable в spec/decision (не chat-only), иначе
следующий apply снова угадывает ногу.

## What Changes

### Intent

Один результат: empty-keywords pause и matching recheck/resume работают только
на Search-ноге (`pause_auction_campaign` / Search start); Auto-адаптер
`pause_auto_campaign` для reason EMPTY_KEYWORDS запрещён; reason code, intent
latch, notify и 7d recheck invariants остаются.

### Current behavior

- После bot-driven last-key OFF V3 ставит Redis empty-keywords intent.
- `AutoAdvActiveControlService._maybe_pause_for_empty_keywords_intent` паузит
  **Auto** через `pause_auto_campaign` и пишет `AutoReasonCode.EMPTY_KEYWORDS`
  на auto reason lane.
- Accepted ADL `empty-keywords-pause-write-path` и main spec
  `pause-on-empty-keywords` говорят «кампания/РК», но не фиксируют ногу Search
  vs Auto и не запрещают Auto adapter для этого reason.
- Competing adapters в runtime: `pause_auto_campaign` и `pause_auction_campaign`.

### Desired behavior

- Empty-keywords pause MUST ставить на паузу **Search** ногу
  (`pause_auction_campaign`).
- Empty-keywords path MUST NOT вызывать `pause_auto_campaign`.
- Recheck/resume для этого reason MUST работать на той же Search-ноге
  (не оставлять Search на паузе, стартуя только Auto «за эту причину»).
- Reason `EMPTY_KEYWORDS`, intent latch, notify, 7d-window invariants — без
  регрессии смысла (кроме target leg).
- Durable SEMANTIC_WRITE_TARGET: TARGET_ENTITY_OR_LEG=SEARCH,
  ALLOWED_ADAPTERS / FORBIDDEN_ADAPTERS materialized в decision + design +
  delta spec + paired tests.
- **Settled-empty gate (warmup ROOT-001 / SPEC_GAP):** empty-keywords Search
  pause MUST NOT arm на Redis warmup-маркере `__empty__` / transient
  zero-active keyword read, пока snapshot warmup ещё может заполнить
  keywords. Distinguishing: warmup false-empty ≠ bot-driven settled empty.
  No-prior-intent arm MUST refuse warmup false-empty so
  `pause_auction_campaign` не срабатывает в этом окне.
- **Notify fanout (notify-fanout ROOT-001 / Owner
  `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`):** empty-keywords pause Telegram
  notify MUST reach ALL shop-linked users with non-null
  `user_telegram_id` via `WBUserCabinet` (same resolution as
  `load_telegram_chat_ids_for_shop` / token NotificationManager «all users
  of a shop»), not only one primary user. Debounce once-per-enter: attempt
  all; KEEP if any delivered.
- **Resume/re-enable notify (no-resume-notify ROOT-001 / SPEC_GAP):** after
  a delivered empty-keywords pause notify, when Search/keywords resume or
  re-enable, MUST send a distinct resume/re-enable Telegram notify to the
  same shop-linked recipients. Pause-entry notify and recheck-mention
  inside the pause message MUST NOT substitute for resume notify.
- **Two-tick empty confirmation before Search pause (puna-empty-shape
  ROOT-001 / Owner `D_TWO_TICK_EMPTY_CONFIRMATION` /
  `TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`):** for no-prior-intent
  settled-empty confirmation, tick1 empty active keywords + Search STARTED
  MUST only record/latch (MUST NOT `pause_auction_campaign`); tick2 still
  empty THEN pause Search (`EMPTY_KEYWORDS`); later tick with keywords
  present → start/resume Search; ticks continue across this lifecycle.
  Warmup Redis `__empty__` remains non-settled (D8); two-tick latch is the
  Owner settled-empty confirmation path when there is no prior V3 intent.

### Scope in

- Retarget empty-keywords pause write-path: Auto → Search.
- ALLOWED: `pause_auction_campaign` (+ matching Search start, если recheck
  требует resume той же ноги).
- FORBIDDEN: `pause_auto_campaign` для EMPTY_KEYWORDS.
- Обновить main capability `pause-on-empty-keywords` (delta) и
  accepted/proposed decision так, чтобы SEARCH был durable.
- Paired tests: Search paused; Auto NOT paused этим path; wrong-adapter
  regression fails if `pause_auto_campaign` used for this reason.
- Keep: reason EMPTY_KEYWORDS, intent latch, notify, 7d recheck.
- Settled-empty vs Redis `__empty__` warmup: durable contract in
  decision + delta spec; implementation guard on no-prior-intent arm;
  RED regression that warmup marker MUST NOT pause Search.
- **Notify fanout (Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`):** User
  notification MUST reach ALL shop-linked Telegram users
  (`WBUserCabinet` + non-null `user_telegram_id`); multi-recipient scenario
  + RED; debounce once-per-enter with any-success KEEP.
- **Resume/re-enable notify (no-resume-notify ROOT-001):** Requirement +
  scenarios + RED/impl tasks for notify after delivered pause notify when
  Search/keywords resume; same recipients; distinct copy.
- **Two-tick empty confirmation (puna-empty-shape ROOT-001 / Owner
  `D_TWO_TICK_EMPTY_CONFIRMATION`):** Requirement + decision + design +
  RED tasks — tick1 latch only (no pause); tick2 still empty →
  `pause_auction_campaign`; later non-empty → Search start/resume; ticks
  continue; warmup `__empty__` still non-settled.

### Out of scope

- Fair Auto/Search billing (`INC-BILL-LEG-PAUSE-01`).
- Tariff 1000₽ (`INC-PRICE-01`).
- `bot_active` disconnect UX, channel comms, onboard/free
  (`INC-DISCONNECT-01` / `INC-COMMS-01` / `INC-ONBOARD-01`).
- Pause BOTH legs / keep Auto pause for empty-keywords.
- Keyword selection, bids, minus, whitelist beyond empty-set hook.
- Process SEMANTIC_WRITE_TARGET meta-fix / command diffs.
- Retire updater v2.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `pause-on-empty-keywords`: target leg = Search; pause via
  `pause_auction_campaign`; forbid `pause_auto_campaign` for EMPTY_KEYWORDS;
  recheck/resume same Search leg.

## Impact

- Shop-runner activity-control empty-keywords pause/recheck seam
  (`_maybe_pause_for_empty_keywords_intent` и связанные Search start/reason
  lanes).
- Accepted ADL `openspec/decisions/empty-keywords-pause-write-path/decision.md`
  → proposed amendment в этом change (leg + adapters).
- Main spec `openspec/specs/pause-on-empty-keywords/spec.md` (через delta).
- Unit/integration tests empty_keywords_pause / activity-control paired matrix.
- Risk: Search absent на комплекте; Auto остаётся STARTED при empty keys
  (осознанный Owner выбор); recheck стартует не ту ногу.
- Rollback idea: вернуть Auto adapter + откатить decision/spec (нежелательно
  без нового Owner decision); feature disable hook как аварийный stop.

## Architecture decisions

- Accepted (cite): `openspec/decisions/empty-keywords-pause-write-path/decision.md`
  — ownership detect → intent → activity-control pause/start + reason + notify
  + 7d; этот change **не** меняет ownership слоёв, а уточняет **target leg /
  adapters**.
- Accepted (cite): `openspec/decisions/mode-defaults-policy-ownership/decision.md`
  — defaults overlays не трогаем.
- Proposed (this change): amendment того же write-path decision —
  TARGET_ENTITY_OR_LEG=SEARCH; ALLOWED=`pause_auction_campaign` (+ Search
  start for recheck); FORBIDDEN=`pause_auto_campaign` for EMPTY_KEYWORDS;
  FORBIDDEN arm/pause on Redis `__empty__` warmup / transient false-empty
  (settled-empty only after bot-driven confirmed empty or equivalent);
  two-tick empty confirmation latch for no-prior-intent
  (Owner `TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`).

## Semantic write target

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: empty-keywords pause / recheck
TARGET_ENTITY_OR_LEG: SEARCH
ALLOWED_ADAPTERS: pause_auction_campaign; matching Search start for recheck/resume
FORBIDDEN_ADAPTERS: pause_auto_campaign (for EMPTY_KEYWORDS reason)
TARGET_EVIDENCE: Owner EVOLUTION_HANDOFF INC-PAUSE-02; competing runtime adapters pause_auto_campaign vs pause_auction_campaign in AutoAdvActiveControlService; current INC-PAUSE-01 path uses pause_auto_campaign
OWNER_DECISION_SOURCE: EVOLUTION_HANDOFF CURRENT_INCREMENT (INC-PAUSE-02) + durable decision/spec in this change
REQUIRED_PAIRED_TESTS: Search paused on empty-keywords; Auto NOT paused by empty-keywords path; wrong-adapter regression fails if pause_auto_campaign is used for this reason
```
