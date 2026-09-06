# FIX-ROOT-001

## Status

Implemented the fail-closed public EXIT guard for missing or invalid Telegram actors.

## Changed paths

- `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py`

## Rationale

`disable_card_ab_hold` now extracts the actor before opening the write session and
returns after notifying the user when the actor is missing or invalid. Therefore
`None` cannot reach `disable_card_ab_hold_in_session` from the public EXIT path,
while the low-level session seam's explicit `telegram_user_id=None` behavior is
preserved for internal callers.

## Commands and results

- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py`
  - PASS: 4 passed.
- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_pg_session_handoff_seams.py tests/unit/auto_updater_v3/card_ab_hold/test_telegram_menu_open_hotfix.py`
  - PASS: 31 passed.
- `git diff --check`
  - PASS.
- IDE lint diagnostics for the changed path
  - PASS: no linter errors.

Warnings were emitted by existing SQLAlchemy and Pydantic deprecations; no test
failures occurred.

ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug
