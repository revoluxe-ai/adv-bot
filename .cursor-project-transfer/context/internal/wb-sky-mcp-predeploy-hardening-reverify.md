---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP predeploy hardening reverify

Independent verify only. No product edits, commit, push, merge, or production action. Local checkout restored to `stage`.

Reviewed `c2cb978a9eb3acab856c90dcd04b7b86accae11d..347edeb1399d8e427e63204811164b71735ceb01` (6 files, +350/−40).

## What the commit does

Telegram `cancel_mcp` now keeps the broker completion URL and attaches `return_keyboard(complete_url)`. `McpBroker.cancel` was already the deny-ticket path; `complete` redirects with `error=access_denied`, original `state`, and `iss`. Cancel does not create a connection row, authorization code, or refresh token.

Refresh exchange calls `apply_refresh_rotation`. PostgreSQL uses `SELECT … FOR UPDATE` and commits in that session. The in-memory repository serializes rotation with one `asyncio.Lock`. Refresh material stays a SHA-256 hash. Redis is not the refresh authority.

## Concurrency

`test_concurrent_refresh_permits_at_most_one_success` runs two in-flight refreshes of the same token via `asyncio.gather` on `MemoryConnectionRepository` and asserts exactly one success. That is the concurrency proof.

`test_sql_refresh_rotation_selects_for_update` only compiles the SQL and checks `FOR UPDATE`. Two live PostgreSQL sessions were not run.

## Pyright

Locked SQLAlchemy 2.0.50: 12 `reportUnknownMemberType` errors, all PyJWT (`encode`/`decode`, `key: Unknown`) or fakeredis (`dbsize`/`keys`, `**kwargs: Unknown`). Two are in `access_token.py` (not in this commit). Ten are in the unit test. `connection_repository.py` is clean on 2.0.50. SQLAlchemy 2.1.3 adds five false `Select[tuple[...]]` errors; that version is not the lockfile.

## WB_SKY_MCP_PREDEPLOY_HARDENING_REVERIFY_REPORT

```text
PR:
#452

REVIEW_HEAD:
347edeb1399d8e427e63204811164b71735ceb01

PARENT_HEAD:
c2cb978a9eb3acab856c90dcd04b7b86accae11d

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

HEAD_STABLE:
YES

COMMIT_SCOPE:
PASS

TELEGRAM_CANCEL_FIX:
PASS

CANCEL_ERROR_REDIRECT:
PASS

CANCEL_STATE_PRESERVED:
PASS

CANCEL_ISS_PRESERVED:
PASS

CANCEL_ISSUES_CODE:
NO

CANCEL_ISSUES_TOKEN:
NO

REFRESH_ROTATION_ATOMIC:
PASS

ROW_LOCK_OR_EQUIVALENT:
PASS

REFRESH_SINGLE_USE:
PASS

CONCURRENT_DOUBLE_REFRESH:
AT_MOST_ONE_SUCCESS

REVOCATION_CHECK:
PASS

AUTHORIZATION_VERSION_CHECK:
PASS

HASHED_AT_REST:
PASS

RUFF:
PASS

PYRIGHT:
ENVIRONMENT_LIMITATION

DIFF_CHECK:
PASS

MCP_TESTS:
35 passed, 0 failed (tests/unit/wb_sky_mcp/test_mcp_read_interface.py)

TELEGRAM_TESTS:
included in MCP_TESTS (test_telegram_cancel_uses_completion_url, test_start_payload_only_mcp_prefix_enters_flow, test_telegram_limits_and_secret_not_in_error_text, test_disabled_start_does_not_mint_and_explain_has_no_token, test_opening_start_does_not_confirm_and_confirm_binds_user_id); no separate Telegram module

AI_PACKAGE_TESTS:
136 passed, 0 failed (tests/unit/ai_package_v1, package conftest)

MIGRATION_TESTS:
PASS (test_exactly_one_alembic_head + test_migration_is_forward_connection_table_without_shop_grants)

OPENSPEC:
PASS

LOCAL_PROTOCOL_EXERCISE:
PASS

PROTOCOL_REGRESSION:
NONE

READ_ONLY_BOUNDARY:
PASS

TOOLS:
get_profile
list_shops
get_capabilities
get_ai_package

WRITE_TOOLS:
NONE

PRODUCT_CODE_CHANGED_BY_REVIEW:
NO

PRODUCTION_CONNECTIVITY:
NONE

PRODUCTION_WRITES:
NONE

CRITICAL:
NONE

HIGH:
NONE

MEDIUM:
NONE

LOW:
PostgreSQL dual-session refresh race was not executed; concurrency proof is MemoryConnectionRepository plus compiled FOR UPDATE

FORMAL_SCENARIO_CERTIFICATION:
PENDING_PREDEPLOY

PREDEPLOY_HARDENING:
PASS

NEXT_GATE:
FORMAL_SCENARIO_CERTIFICATION

FINAL_STATUS:
PREDEPLOY_HARDENING_PASS
```
