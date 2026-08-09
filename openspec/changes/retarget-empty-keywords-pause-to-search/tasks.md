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
- [ ] 6.3 После verify: обновить `LINKED_CHANGES` / INC-PAUSE-02 evidence на карточке звезды (не расширять DoD).

<!-- OWNER_CORRECTION (antipattern FAIL, not a task checkbox): 2026-08-08
  Un-exported `stats_window_compatible_with_recheck` and `STATS_WINDOW_DAYS_MAX`
  from `empty_keywords_pause/__init__.py` public `__all__` (remain on `decision.py`;
  tests import module-direct). Rewrote product docstring on
  `stats_window_compatible_with_recheck` (7d invariant; no «тест MUST падать»).
  DISPATCH D-APPLY-ANTI-01 / MISSION-PAUSE02-GATES-20260808. -->
