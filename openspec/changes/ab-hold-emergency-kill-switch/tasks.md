## 1. Tests-first (RED)

- [x] 1.1 Добавить unit-тесты visibility: Emergency скрыт при Hold `OFF`, виден при non-`OFF` (spec: Emergency control visible only under A/B Hold)
- [x] 1.2 Добавить unit-тесты launch education Confirm/ACK обязателен (spec: Launch education before relying on Emergency)
- [x] 1.3 Добавить unit-тесты confirm-on-press: cancel = no mutations; confirm = pause+block+latch (spec: Confirm before Emergency executes)
- [x] 1.4 Добавить unit-тесты executor: pause + block-all + latch ACTIVE; Hold mode не → `OFF` (spec: Emergency stops spend immediately)
- [x] 1.5 Добавить unit-тесты идемпотентности при уже ACTIVE latch (spec: Emergency is idempotent)
- [x] 1.6 Добавить unit-тесты gate: `ensure_budget` / activity restart MUST NOT top-up/restart при ACTIVE latch (paired positive: latch OFF разрешает ordinary path)
- [x] 1.7 Добавить Telegram payload-limit тесты для education / confirm / result+support текстов (см. § Telegram UI)

## 2. Durable latch SoT

- [x] 2.1 Выбрать и задокументировать в design note / комментарии миграции PG-поле Emergency latch (scan AdvSetting / card_ab_hold state)
- [x] 2.2 Добавить Alembic-миграцию + модель SQLAlchemy для latch (default OFF/false)
- [x] 2.3 Добавить read/write helpers latch с docstring (spec + decision write-path)

## 3. Emergency executor (write-path)

- [x] 3.1 Реализовать Emergency service/orchestrator: idempotent check → pause_adv → block-all keywords → set latch (decision carve-out; не EXIT Hold)
- [x] 3.2 Подключить pause через существующий `pause_adv` / promotion pause adapters (ComplexAdv Search+Auto) — force-pause в activity-control при latch; прямой bot→WB pause optional follow-up
- [x] 3.3 Реализовать owned bulk block-all (hard_status BLACK_LIST или эквивалент) вне ordinary freeze handlers
- [x] 3.4 Вставить latch gate в auto-budget top-up и activity-control restart пути
  (manager candidates + `ensure_budget`/`ensure_common_budget` early return + activity force-pause)
- [x] 3.5 Честный partial-failure статус (pause/latch OK, block partial) — без silent success

## 4. Telegram UI

- [x] 4.1 Кнопка Emergency только на Hold screens при mode ≠ `OFF`
- [x] 4.2 Launch/start education Confirm/ACK (объяснение pause+block+no top-up+«что-то не то»)
- [x] 4.3 Confirm «Точно остановить?» перед executor
- [x] 4.4 Result / active-emergency экран с `const.SUPPORT_LINK` (сразу контакт)
- [x] 4.5 MVP: не добавлять self-serve «снять аварию / сброс в обычный» (spec out of MVP)

## 5. Verification

- [x] 5.1 Прогнать targeted unit suite Emergency + смежные freeze gates (не ломая PBH-010/011)
- [x] 5.2 `poetry run pyright-strict` на затронутых модулях
- [x] 5.3 `/opsx-bug-hunt` (или project hunt focus emergency) после apply
- [x] 5.4 Отметить decision review checklist «implementation layer matches decision» после размещения кода

## Telegram UI / Message Safety

- [x] Identify every changed Telegram payload surface (education, confirm, result, support button/url, callback answers).
- [x] Add/update tests with worst-case dynamic placeholder data (длинные названия РК, много ключей в summary).
- [x] Assert Telegram Bot API limits from `openspec/policies/telegram_bot_api_limits.md`.
- [x] Assert valid parse_mode / escaping.
- [x] Assert callback_data length in UTF-8 bytes.
- [x] Assert no raw technical text leaks to user.
