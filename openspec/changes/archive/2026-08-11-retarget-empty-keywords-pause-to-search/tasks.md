## 1. Tests-first / paired matrix (до production)

- [x] 1.1 Characterization: зафиксировать текущий INC-PAUSE-01 path — empty-keywords intent → `pause_auto_campaign` + Auto-lane `empty_keywords` (baseline перед retarget).
- [x] 1.2 Unit tests-first (positive): intent → Search paused через `pause_auction_campaign`; Search-lane reason `empty_keywords`; notify — по spec «Pause campaign after last keyword off by bot» / «Empty-keywords pause targets Search leg only».
- [x] 1.3 Unit tests-first (paired negative): тот же path MUST NOT await `pause_auto_campaign` — Auto NOT paused by empty-keywords path.
- [x] 1.4 Wrong-adapter regression: тест MUST падать, если empty-keywords path вызывает `pause_auto_campaign` (удаление/ослабление forbid gate ломает тест).
- [x] 1.5 Unit tests-first recheck: Search pause по empty-keywords → Search start (не Auto-only) → при снова empty → Search re-pause; scenario «Auto-only start does not satisfy empty-keywords recheck».
- [x] 1.6 Missing Search leg: empty-keywords path MUST NOT pause Auto — по scenario «Missing Search leg does not pause Auto».
- [x] 1.7 Сохранить инварианты: reason ≠ schedule/budget/cost; 7d gate; Hold не EXIT в OFF из-за empty-keywords (существующие тесты обновить под Search, не удалять смысл).

## 2. Reason code Search lane

- [x] 2.1 Добавить `AuctionReasonCode.EMPTY_KEYWORDS = "empty_keywords"` + display mapping (тот же UI-label); Auto-lane MUST NOT выставляться этим path.
- [x] 2.2 Docstrings на русском со ссылкой на spec requirement для enum/display/хелперов.

## 3. Retarget pause write-path

- [x] 3.1 В empty-keywords activity-control seam заменить pause на `pause_auction_campaign`; условие STARTED — по Search status; записать Search reason `empty_keywords` + notify.
- [x] 3.2 Убрать/запретить `pause_auto_campaign` из empty-keywords path (согласовано с 1.3/1.4).
- [x] 3.3 Нет Search-ноги: skip pause write без Auto fallback (согласовано с 1.6); structured log.
- [x] 3.4 Не менять V3 keyword selection / bid / whitelist / minus; detect/intent latch сохранить.

## 4. Recheck / resume на Search

- [x] 4.1 Обеспечить периодический Search start при Search pause по empty-keywords без более приоритетного Search blocker (matching ALLOWED Search start adapter).
- [x] 4.2 После recheck: keys empty → снова Search pause + reason; keys active → не держать Search на empty-keywords pause.
- [x] 4.3 Миграция: старый Auto-lane `empty_keywords` от INC-PAUSE-01 не удерживает Auto на паузе «ради» empty-keywords (ordinary Auto path / clear).

## 5. Notify / UX (без расширения copy-scope)

- [x] 5.1 Прогнать существующие message/notify тесты после retarget; при необходимости уточнить, что пауза относится к Search, без канал-анонса и без смены SUPPORT_LINK контракта.

## Telegram UI / Message Safety

- [x] T1 Identify every changed Telegram payload surface (если copy меняется).
- [x] T2 Add/update tests with worst-case dynamic placeholder data.
- [x] T3 Assert Telegram Bot API limits from `openspec/policies/telegram_bot_api_limits.md`.
- [x] T4 Assert valid parse_mode / escaping.
- [x] T5 Assert callback_data length in UTF-8 bytes (если есть callback-кнопки).
- [x] T6 Assert no raw technical text leaks to user (`EMPTY_KEYWORDS` / adapter names не в сыром виде).

## 6. Границы change / verification prep

- [x] 6.1 Targeted unit (+ нужные integration) для Search/Auto paired matrix; `poetry run pyright-strict` на затронутых модулях при необходимости.
- [x] 6.2 Проверить отсутствие EVOLUTION_SCOPE_DRIFT: нет billing/tariff/disconnect/comms/onboard/BOTH-legs/v2 tasks в коде.
- [x] 6.3 После verify: обновить `LINKED_CHANGES` / INC-PAUSE-02 evidence на карточке звезды (не расширять DoD).
  Evidence (2026-08-11): `openspec/evolution/affordable-auto-pause-on-empty.md` INC-PAUSE-02 — LINKED_CHANGES unchanged (`retarget-empty-keywords-pause-to-search`); Evidence/completion updated after archive-verify ✅ GO / PA PASS (archive move still pending Owner sync confirm).

## 7. Settled-empty vs Redis `__empty__` warmup (ROOT-001 / SPEC_GAP)

- [x] 7.1 Spec/decision contract: в delta spec + proposed `empty-keywords-pause-write-path` зафиксировать settled-empty vs Redis `__empty__` warmup false-empty (no-prior-intent MUST NOT arm на warmup marker / transient empty).
- [x] 7.2 Implementation guard: в empty-keywords arm seam (`_maybe_pause_for_empty_keywords_intent` / `should_request_empty_keywords_pause_intent` + settled-empty / warmup-marker signal) запретить arm+`pause_auction_campaign` при warmup `__empty__` / transient false-empty без settled-empty confirmation; не ломать bot-driven settled empty и recheck после settled pause; не отключать intentional re-fetch `[]` в `get_keywords`.
- [x] 7.3 RED regression (tests-first via `/opsx-test` before production GO): Search STARTED + Redis `__empty__` (или эквивалентный transient empty) + no prior V3 intent + no bot-driven OFF → MUST NOT await `pause_auction_campaign` / MUST NOT set Search-lane EMPTY_KEYWORDS; paired allowed: bot-driven settled empty всё ещё паузит Search.

## 8. Notify fanout — all shop-linked Telegram users (ROOT-001 / SPEC_GAP notify-fanout)

Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`: empty-keywords pause notify MUST
reach ALL users linked to the shop via `WBUserCabinet` with non-null
`user.user_telegram_id` (same resolution as `get_wb_user_cabinets_for_shop` /
`load_telegram_chat_ids_for_shop`). Debounce once-per-enter: attempt all;
KEEP if any delivered; RELEASE if none.

- [x] 8.1 Spec/decision/design contract: delta `User notification on empty-keywords pause` MUST all shop-linked recipients + scenario «Multi-recipient fanout…»; proposed decision notify clause + design D7/Ownership; debounce any-success KEEP documented.
- [x] 8.2 RED regression (tests-first via `/opsx-test` before production GO): shop with ≥2 distinct `WBUserCabinet` telegram chat_ids → after empty-keywords Search pause enter, `send_message` awaited for **each** chat_id (not only one); paired: debounce KEEP on any-success / RELEASE on all-fail remains.
  Evidence (ROOT-001 / BUGCASE-EMPTY-KW-NOTIFY-FANOUT-20260809T212511Z): RED `PASS_ALREADY` + GREEN `GREEN_CONFIRMED` for multi-chat fanout suite `test_notify_multi_chat_fanout.py` (send_message each chat_id + paired KEEP/RELEASE); see `results/RED-ROOT-001.md`, `results/GREEN-ROOT-001.md`.
- [ ] 8.3 Implementation (only if RED exposes gap after contract): ensure `notify_empty_keywords_pause` fans out to all resolved chat_ids; no single-primary hardcode; do not expand recipient scope beyond WBUserCabinet + non-null telegram id without new Owner decision.
  CANCELLED/N/A — not required PASS_ALREADY (no production gap): RED immediate-green on unchanged `notify.py`; IMPLEMENTATION_EXECUTOR skipped; do **not** mark done-as-implemented. Evidence: `results/RED-ROOT-001.md`, `results/GREEN-ROOT-001.md`, `results/TASK-DELTA-ROOT-001.md`.

## 9. Resume/re-enable notify after empty-keywords pause (ROOT-001 / SPEC_GAP no-resume-notify)

Owner field report (BUGCASE-EMPTY-KW-NO-RESUME-NOTIFY): pause-for-empty-keywords
Telegram notify arrived; resume/re-enable notify when keywords/campaign turned
back on did **not**. After a **delivered** empty-keywords pause notify, when
Search/keywords resume or re-enable, MUST notify the same shop-linked recipients
with a message **distinct** from pause-entry and from recheck-mention inside
the pause message.

- [x] 9.1 Spec/decision/design contract: delta Requirement `User notification on empty-keywords resume/re-enable` + scenarios (resume after pause notify; same recipients; distinct from pause-entry/recheck-mention; no resume without prior pause notify); proposed decision clause 8; design D7b / Ownership row.
- [x] 9.2 RED regression (tests-first via `/opsx-fix-bug` / `/opsx-test` before production GO): after delivered empty-keywords pause notify + Search resume / keywords re-enable → `send_message` resume/re-enable text for **each** shop-linked chat_id; paired: resume text ≠ pause-entry; no resume notify without prior delivered pause notify episode.
  Evidence (ROOT-001 / BUGCASE-EMPTY-KW-NO-RESUME-NOTIFY-20260809T214041Z): RED `RED_CONFIRMED` (3 fail ImportError missing resume notify) + GREEN `GREEN_CONFIRMED` for suite `test_notify_resume_after_pause.py` (fanout + distinct text + no resume without prior pause episode); see `results/RED-ROOT-001.md`, `results/GREEN-ROOT-001.md`.
- [x] 9.3 Implementation (after RED fails / exposes gap): add resume/re-enable notify emit (sibling of `notify_empty_keywords_pause` / message builder) on Search/keywords resume after empty-keywords pause episode; same recipient resolution as pause fanout; do not redesign pause write-path / adapters; do not treat pause-entry or recheck-mention as sufficient.
  Evidence (ROOT-001 / BUGCASE-EMPTY-KW-NO-RESUME-NOTIFY-20260809T214041Z): FIX `FIXED` (`notify_empty_keywords_resume` + message builder + Search-start call-site) + GREEN `GREEN_CONFIRMED` same frozen suite; see `results/FIX-ROOT-001.md`, `results/GREEN-ROOT-001.md`.

## 10. Two-tick empty confirmation before Search pause (ROOT-001 / SPEC_GAP puna-empty-shape)

Owner `D_TWO_TICK_EMPTY_CONFIRMATION` /
`TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE` (BUGCASE-EMPTY-KW-PUNA-EMPTY-SHAPE):
for no-prior-intent settled-empty confirmation — tick1 empty + Search
STARTED = record/latch ONLY (MUST NOT `pause_auction_campaign`); tick2
still empty = THEN pause Search (`EMPTY_KEYWORDS`); later tick keywords
present = start/resume Search; ticks continue. Warmup Redis `__empty__`
remains non-settled (section 7 / D8); two-tick latch is the Owner
settled-empty confirmation path when there is no prior V3 intent.

- [x] 10.1 Spec/decision/design contract: delta Requirement
  `Two-tick empty confirmation before Search pause` + scenarios (tick1
  latch no pause; tick2 pause; later non-empty start/resume; ticks
  continue); proposed decision clause 9; design D9 / Ownership row.
- [x] 10.2 RED regression (tests-first via `/opsx-fix-bug` / `/opsx-test`
  before production GO):
  - tick1 empty + Search STARTED + no prior settled latch → intent/latch
    set, `pause_auction_campaign` NOT awaited;
  - tick2 still empty → `pause_auction_campaign` fires + Search-lane
    EMPTY_KEYWORDS;
  - later non-empty → Search start path available (existing resume
    behavior may remain).
  Paired: warmup `__empty__` still MUST NOT count as tick1 settled
  confirmation (section 7).
- [x] 10.3 Implementation (after RED fails / exposes gap): durable
  two-tick latch in empty-keywords arm/decision seam; forbid same-tick
  arm+pause on first empty observe for no-prior-intent; preserve D8
  warmup non-settled; do not stop ticks; do not redesign Search/Auto
  adapters matrix.

<!-- OWNER_CORRECTION (antipattern FAIL, not a task checkbox): 2026-08-08
  Un-exported `stats_window_compatible_with_recheck` and `STATS_WINDOW_DAYS_MAX`
  from `empty_keywords_pause/__init__.py` public `__all__` (remain on `decision.py`;
  tests import module-direct). Rewrote product docstring on
  `stats_window_compatible_with_recheck` (7d invariant; no «тест MUST падать»).
  DISPATCH D-APPLY-ANTI-01 / MISSION-PAUSE02-GATES-20260808. -->
