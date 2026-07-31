## Why

Во время A/B Hold пользователь может столкнуться с неконтролируемым сливом бюджета (разгон, гонка activity-control/top-up, сбой статистики). Нужен явный **Emergency** kill switch: мгновенно остановить траты (пауза РК, блок всех ключей, запрет пополнения бюджета) **только внутри режима A/B Hold**, с обязательным объяснением на странице запуска и немедленным контактом с поддержкой. Это **не** часть write-path A/B Hold (`card-ab-hold-mode` ADL §18 запрещает emergency-stop / global refill suppression как владение Hold) — отдельный follow-on product control.

## What Changes

### Intent

Один paid Telegram-контроль **Emergency** для кампаний в A/B Hold: кнопка видна только пока Hold ≠ `OFF`; на странице запуска Hold — обязательное образование (Confirm/ACK); по нажатию — confirm «Точно остановить?» → пауза РК + блок всех ключей + durable latch «бюджет не пополняется / activity не рестартит» → результат с ссылкой на поддержку (`SUPPORT_LINK`). Hold mode **не** EXIT’ится: траты гасятся carve-out’ом поверх freeze. Снятие аварии и сброс в обычный режим — later (не MVP), но UX уже сообщает, что нажатие = «что-то сильно не то» и нужен контакт.

### Current behavior

- В A/B Hold structural freeze блокирует ordinary whitelist / hard_status / common-bid и т.п.; отдельного Emergency kill switch нет.
- Пауза РК и auto-budget watchdog уже существуют как ортогональные пути activity-control / top-up, но нет единого «аварийного» действия с latch против повторного start+top-up.
- `card-ab-hold-mode` §18 явно запрещает вводить emergency-stop / global refill suppression **как часть** Hold write-path; anti-drain parked в WORKLOG как deferred follow-on.
- Поддержка уже имеет `SUPPORT_LINK` (`https://t.me/sky_manager_1`).

### Desired behavior

- Кнопка Emergency **только** при A/B Hold mode ∈ {PENDING_SETUP, WARM_UP, ACTIVE, …} — все non-`OFF` фазы; на ordinary РК (Hold `OFF`) кнопки нет.
- На **странице запуска Hold** — обязательное объяснение (Confirm/ACK popup или эквивалент); silent button Forbidden.
- Перед исполнением — короткий confirm на нажатие.
- По confirm: (1) pause campaign(s); (2) block all keywords; (3) set durable Emergency latch → no budget top-up / no activity restart while latch ACTIVE; (4) показать результат + сразу ссылку/кнопку поддержки.
- Идемпотентность: повторное нажатие при уже ACTIVE latch — no-op с честным статусом.
- Hold mode остаётся; Ordinary freeze handlers остаются Forbidden для пользователя; Emergency — **owned carve-out** write-path (отдельный ADL).
- MVP **не** включает one-tap «снять аварию / сброс в обычный режим» (later + поддержка).

### Scope in

- Hold-only Emergency UI (меню A/B Hold + education на launch).
- Confirm-on-press.
- Pause adv + bulk keyword block + refill/restart suppress latch (durable SoT).
- Immediate support contact via existing `SUPPORT_LINK`.
- Proposed write-path architecture decision (ownership carve-out vs Hold freeze / §18).
- Unit/integration tests + Telegram payload limits.
- ComplexAdv Search+Auto пары (primary scope).

### Out of scope

- Reopen / amend DoD `card-ab-hold-mode` или smuggle emergency into Hold §18 ownership.
- Pre-start hard|soft|self picker; mid-sync wait|force|EXIT UX (уже parked deferred).
- One-tap undo / «снять аварийный стоп → обычный режим» (later).
- Emergency на ordinary campaigns (Hold `OFF`).
- Rich audit journal / monitoring-alerting evidence-driven auto-stop.
- Single-leg non-ComplexAdv (unless trivial reuse; not MVP DoD).
- Изменение текста `SUPPORT_LINK` / смена support-аккаунта.

## Capabilities

### New Capabilities

- `ab-hold-emergency-kill-switch`: Hold-only Emergency control — visibility, launch education, confirm, pause+block+latch, support CTA, idempotency.

### Modified Capabilities

- (none at main-spec level in MVP; Hold freeze requirements stay; Emergency is additive carve-out documented in this change’s delta if needed for cross-links)

## Impact

- Paid Telegram A/B Hold UI и handlers.
- Campaign pause path (`pause_adv` / activity-control).
- Keyword hard_status / bulk block path (carve-out under Hold freeze).
- Auto-budget / activity-control top-up and restart gates (durable Emergency latch).
- New proposed ADL under this change; must not contradict Hold §18 by claiming Hold owns emergency.
- Risk: mid-sync partial block, double-press, activity-control fighting pause without latch, collision with dirty PBH freeze gates in same worktree — serialize apply vs uncommitted Hold bugfixes.
- Rollback idea: feature-flag / hide button + clear latch column default OFF; pause/block remain reversible via support later path.
