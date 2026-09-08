# GREEN evidence: ROOT-001

## Status

- GREEN status: PASS
- Verification was performed independently from the executor self-report.

## Frozen test integrity

- Frozen test: `tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py`
- Expected SHA-256: `dfecfb3e51d1a771dbe4750f742de6ae0133216b3f0a692981e2cd4dba0a360e`
- Observed SHA-256: `dfecfb3e51d1a771dbe4750f742de6ae0133216b3f0a692981e2cd4dba0a360e`
- Result: MATCH
- Frozen test was not modified.

## Commands and results

- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py`
  - PASS: 4 passed, 1 warning.
- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_pg_session_handoff_seams.py tests/unit/auto_updater_v3/card_ab_hold/test_telegram_menu_open_hotfix.py`
  - PASS: 31 passed, 5 warnings.
- `git diff --check`
  - PASS.

The warnings are existing SQLAlchemy and Pydantic deprecations; no test
failures occurred.

## Invariant and scope

- Invariant verified: the public `disable_card_ab_hold` EXIT handler rejects a
  missing or invalid actor before opening the write session, so no PG mutation
  or commit occurs for that input.
- The public handler extracts and validates the actor before `async with
  sm(read_only=False)`.
- The internal `disable_card_ab_hold_in_session` seam remains available for
  internal callers; its `telegram_user_id=None` behavior is unchanged.
- Changed production scope is limited to
  `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py`.

EVIDENCE_PATH=results/GREEN-ROOT-001.md
