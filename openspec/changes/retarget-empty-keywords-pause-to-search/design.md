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
- Settled-empty vs Redis `__empty__` warmup: no-prior-intent arm MUST NOT
  pause Search на transient warmup false-empty (warmup ROOT-001).
- Notify fanout: MUST all shop-linked Telegram users (notify-fanout ROOT-001 /
  Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`).
- Resume/re-enable notify (no-resume-notify ROOT-001 / SPEC_GAP): после
  доставленного empty-keywords pause notify, при Search/keywords resume
  или re-enable — отдельный Telegram notify тем же shop-linked
  recipients; distinct от pause-entry и recheck-mention в pause message.
- Two-tick empty confirmation before Search pause (puna-empty-shape
  ROOT-001 / Owner `D_TWO_TICK_EMPTY_CONFIRMATION`): tick1 empty →
  record/latch only (MUST NOT pause Search); tick2 still empty → THEN
  `pause_auction_campaign`; later keywords → start/resume Search; ticks
  continue. Warmup `__empty__` remains non-settled (D8).

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
  (Proposed) — TARGET_ENTITY_OR_LEG=SEARCH; ALLOWED/FORBIDDEN adapters;
  settled-empty vs `__empty__`; User notify MUST all shop-linked recipients
  (Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`); User notify on
  resume/re-enable after delivered pause notify (no-resume-notify ROOT-001);
  two-tick empty confirmation latch
  (`TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE` / puna-empty-shape ROOT-001).
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
| Notify fanout (pause entry) | `notify_empty_keywords_pause` → `load_telegram_chat_ids_for_shop` / `get_wb_user_cabinets_for_shop` → `NotificationSender.send_message` per chat_id | Single-primary hardcode; channel/marketing copy; non-cabinet UX links without contract |
| Notify resume/re-enable | empty-keywords resume notify emit (sibling of pause notify; same recipient resolution) after delivered pause-notify episode when Search/keywords resume | Treating pause-entry or recheck-mention as resume notify; ordinary Search start spam without prior pause-notify episode; single-primary hardcode |
| Two-tick empty confirmation (no-prior-intent) | empty-keywords arm/decision seam: tick1 latch/record only; tick2 still-empty → Search pause; later non-empty → Search start/resume; ticks continue | Same-tick arm+`pause_auction_campaign` on first empty observe; treating warmup `__empty__` as settled; skipping latch and pausing on tick1 |

Placement MUST match proposed amended `empty-keywords-pause-write-path`.

**Notify fanout ownership (ROOT-001 / BUGCASE-EMPTY-KW-NOTIFY-FANOUT):**
Recipient scope MUST be all shop-linked Telegram users via WBUserCabinet +
non-null `user_telegram_id` (align token NotificationManager «all users of a
shop»). Owner decision `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`. Debounce
once-per-enter stays: attempt all chat_ids; keep debounce if any delivery
succeeds; release if none delivered.

**Resume/re-enable notify ownership (ROOT-001 /
BUGCASE-EMPTY-KW-NO-RESUME-NOTIFY):**
After a delivered empty-keywords pause notify, when Search/keywords resume
or re-enable, MUST emit a distinct resume/re-enable Telegram notify to the
same shop-linked recipient set. Placement: UX notify seam next to pause
notify (not redesign of pause write-path / adapters). Pause-entry text and
recheck-mention inside pause message MUST NOT substitute for resume notify.

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

## Product Acceptance

```text
PRODUCT_ACCEPTANCE_REQUIRED: true
SCENARIO_COVERAGE_REQUIRED: true
REASON: SEMANTIC_WRITE_TARGET (Search vs Auto) + EVOLUTION_LINK INC-PAUSE-02
  + material Search pause/start + paid Telegram notify lifecycle
```

## OWNER_LIFECYCLE_ECHO

Упорядоченный смысл во времени (INC-PAUSE-02 / pause-on-empty-keywords):

1. После bot-driven OFF последнего ключа **или** на тике наблюдаем settled empty
   активных ключей при Search STARTED (warmup Redis `__empty__` / transient
   false-empty **не** считаются settled).
2. Tick1 (no prior intent): только latch/intent — **без** `pause_auction_campaign`
   и без Search pause в этом тике.
3. Tick2 (всё ещё empty) **или** consume уже settled intent: пауза **только Search**
   (`pause_auction_campaign` + Search-lane `empty_keywords`); Auto **не** паузится
   этим path (`pause_auto_campaign` Forbidden); нет Search-ноги → skip, не Auto fallback.
4. При входе в Search pause — Telegram notify **всем** shop-linked recipients
   (debounce once-per-enter, any-success KEEP).
5. Пока Search на empty-keywords pause: периодический recheck стартует **Search**;
   Auto-only start не закрывает recheck; снова empty → снова Search pause.
6. После **доставленного** pause notify, когда Search/keywords resume/re-enable —
   отдельный resume notify тем же recipients (не pause-entry / не recheck-mention).

`CONFIRM_LIFECYCLE`: **confirmed** (Owner, 2026-08-11) — echo accepted; PA MEANING_LOCK + Owner lifecycle spirit locked; scenario report still required before archive verify GO.

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

### D7. Notify / UX — all shop-linked recipients

**Выбор:** переиспользовать существующий notify text (причина + перепроверка);
при необходимости уточнить, что на паузе Search-нога — только если copy уже
говорит «кампания» двусмысленно; не раздувать в канал-анонс (out of scope).

**Recipient scope (Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`):** notify MUST
доставляться **всем** пользователям магазина с `WBUserCabinet` и non-null
`user.user_telegram_id` — тот же resolution, что
`get_wb_user_cabinets_for_shop` / `load_telegram_chat_ids_for_shop`
(семантика token `NotificationManager` «all users of a shop»). MUST NOT
ограничивать одним primary recipient при нескольких chat_id.

**Debounce:** once-per-enter остаётся. MUST пытаться доставить всем resolved
chat_id; debounce-ключ KEEP, если хотя бы одна доставка успешна; RELEASE,
если ни одна не успешна (partial failure при any-success не снимает ключ).

**Paired RED:** ≥2 distinct shop-linked telegram chat_ids →
`send_message` для каждого; singular-only path Forbidden.

### D7b. Resume/re-enable notify after pause episode (no-resume-notify ROOT-001)

**Проблема:** accepted/delta pause notify покрывает только вход в паузу
(причина + упоминание перепроверки). Owner field report: pause notify
пришёл, notify что кампания/ключи снова включены — нет. OpenSpec был
silent → SPEC_GAP.

**Выбор:** после **доставленного** empty-keywords pause notify, когда
Search/keywords resume или re-enable после этого episode, MUST отправить
отдельный resume/re-enable Telegram notify. Recipients = тот же
all shop-linked scope, что D7 / Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`.
Текст MUST быть distinct от pause-entry и от recheck-mention в pause
message. Ordinary Search start без prior delivered pause-notify episode
MUST NOT слать этот resume notify.

**Placement:** empty-keywords notify package / activity-control resume
seam (emit после успешного Search resume/re-enable «за» empty-keywords
pause episode); не менять TARGET_ENTITY_OR_LEG / pause adapters.

**Paired RED:** delivered pause notify → Search resume / keywords
re-enable → `send_message` resume text to each shop-linked chat_id;
paired negative: no prior pause notify → no resume notify; resume text ≠
pause-entry / recheck-mention-only.

### D8. Settled-empty vs Redis `__empty__` warmup (ROOT-001)

**Проблема:** `ComplexAdv.get_keywords` при Redis-маркере `__empty__`
возвращает `[]` и **намеренно** перечитывает каждый tick (snapshot warmup
может позже записать keywords). Activity-control no-prior-intent arm
(`_maybe_pause_for_empty_keywords_intent` →
`should_request_empty_keywords_pause_intent` при `active_count==0` +
Search STARTED + `bot_driven_off_completed=False`) может в этом окне
вооружить intent и вызвать `pause_auction_campaign` — false pause на
warmup, не на bot-driven settled empty.

**Выбор:** empty-keywords Search pause / no-prior-intent arm MUST требовать
**settled empty** (bot-driven confirmed empty после OFF / эквивалентный
durable сигнал settled empty). Redis `__empty__` warmup marker и любой
transient zero-active read, пока warmup ещё может populate keywords,
MUST NOT считать settled empty и MUST NOT arm intent / pause Search.

**Allowed arm sources (unchanged intent):**
- V3 post-OFF intent после bot-driven last-key OFF (settled empty);
- recheck path после уже settled empty-keywords pause (снова empty после
  Search start) — не путать с первым warmup read.

**Forbidden:**
- трактовать `__empty__` / first-tick `[]` как settled empty;
- no-prior-intent arm → `pause_auction_campaign` только из warmup marker.

**Placement:** guard в empty-keywords decision/arm seam (activity-control
и/или `should_request_empty_keywords_pause_intent` + явный settled-empty /
warmup-marker signal); не ломать intentional re-fetch `[]` в
`get_keywords` для warmup populate.

**Paired RED:** Search STARTED + Redis `__empty__` / transient empty +
нет prior V3 intent + нет bot-driven OFF → MUST NOT `pause_auction_campaign`
/ MUST NOT set EMPTY_KEYWORDS reason.

### D9. Two-tick empty confirmation before Search pause
(puna-empty-shape ROOT-001 / Owner `D_TWO_TICK_EMPTY_CONFIRMATION`)

**Проблема:** accepted/delta D8 различает warmup Redis `__empty__` vs
settled-empty, но **не** кодирует Owner lifecycle для no-prior-intent:
«ключи реально пусты и Search STARTED — можно ли сразу паузить без
старого intent? — нет; фиксируем; после второго тика снова пусто —
тогда пауза; тики продолжаются; позже если ключи есть — включается РК».
Текущий same-tick arm+`pause_auction_campaign` на первом empty observe
конфликтует с этим правилом.

**Выбор (Owner `TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`):**

1. **Tick1** — empty active keywords + Search STARTED: MUST
   record/latch only (intent / confirmation latch). MUST NOT
   `pause_auction_campaign` / MUST NOT поставить Search на паузу по
   EMPTY_KEYWORDS в этом тике.
2. **Tick2** — всё ещё empty: THEN pause Search
   (`pause_auction_campaign` + Search-lane `empty_keywords`).
3. **Later tick** — keywords present: MUST иметь путь start/resume
   Search (существующий recheck/resume behavior может остаться).
4. **Ticks continue** across this lifecycle (не останавливать тики
   после latch или после pause).

**Отношение к D8:** Redis warmup `__empty__` остаётся **non-settled**
и MUST NOT arm даже tick1 latch как settled confirmation.
Two-tick latch — Owner settled-empty confirmation path для
**no-prior-intent** (когда нет prior V3 bot-driven intent). Bot-driven
V3 post-OFF intent path (settled empty после OFF) остаётся allowed
arm source из D8 и не обязан проходить «два тика наблюдения» заново,
если intent уже установлен как settled confirmation.

**Placement:** empty-keywords decision/arm seam в activity-control
(или рядом с `should_request_empty_keywords_pause_intent` /
`_maybe_pause_for_empty_keywords_intent`): durable per-komplekt /
per-adv latch across ticks; pause write только после второго
подтверждённого empty tick.

**Paired RED (owed):**
1. Tick1 empty + Search STARTED + no prior settled latch → intent/latch
   set, `pause_auction_campaign` NOT awaited.
2. Tick2 still empty → `pause_auction_campaign` fires + Search-lane
   EMPTY_KEYWORDS.
3. Later non-empty → Search start/resume path available (existing
   resume behavior may remain).

## Risks / Trade-offs

- [Auto остаётся STARTED при пустых ключах] → осознанный Owner trade-off
  INC-PAUSE-02; billing fair-pause — отдельный increment.
- [Нет Search-ноги] → skip, no Auto fallback; мониторить skip logs.
- [Recheck стартует Auto, Search забыт] → paired test D6.4; Search reason gate.
- [Старые Auto EMPTY_KEYWORDS в Redis] → D5 clear via ordinary Auto path.
- [parse_reason_code предпочитает Auto enum при shared value] → уже паттерн
  для common codes; display по string value; tests на value `empty_keywords`.
- [Warmup `__empty__` → premature Search pause] → D8 settled-empty gate +
  RED regression; не отключать re-fetch `[]` в `get_keywords`.
- [Same-tick arm+pause on first empty observe] → D9 two-tick latch +
  RED (tick1 no pause / tick2 pause); не путать с warmup `__empty__`.

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
