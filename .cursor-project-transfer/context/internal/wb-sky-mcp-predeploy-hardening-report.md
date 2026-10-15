---
cursor:
  subagentId: "bc-c2a8910f-b736-5484-8906-769fa0981b8f"
---

# WB_SKY_MCP_PREDEPLOY_HARDENING_REPORT

Change `wb-sky-mcp-read-interface`. PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) on `cursor/wb-sky-mcp-read-interface-127c`. Not merged. No production action.

Telegram cancel now attaches the existing broker completion URL (`return_keyboard`) so the OAuth client receives `error=access_denied` with the original `state` and exact `iss`. No second cancel mechanism. No code and no tokens.

Refresh rotation is one critical section: PostgreSQL `SELECT … FOR UPDATE` plus write in the same transaction (`SqlConnectionRepository.apply_refresh_rotation`); the in-memory test seam uses one `asyncio.Lock`. Hashed-at-rest refresh storage stays in PostgreSQL. Two concurrent uses of the same refresh yield exactly one success; the waiter observes the rotated previous hash and fails closed. Replay, revocation, and a bumped authorization version fail. Access `expires_in` and refresh TTL stay on the current config.

Prior protocol findings were not reopened. The same ASGI unit suite still covers CIMD `none`, initialize negotiation, notifications, HTTP 401 + `WWW-Authenticate`, `_meta["mcp/www_authenticate"]`, tool `securitySchemes`, `iss`, resource binding, PKCE S256, Streamable HTTP, dynamic shop grants, and the four read-only tools.

Pyright 1.1.411 against the Poetry 3.11 env: 0 errors on `app/modules/wb_sky_mcp` and `tests/unit/wb_sky_mcp`. The earlier 10 `reportUnknownMemberType` hits on `jwt` / `fakeredis` did not reproduce; no ignores were added.

```text
PR:
#452

BASE_HEAD:
c2cb978a9eb3acab856c90dcd04b7b86accae11d

FINAL_HEAD:
347edeb1399d8e427e63204811164b71735ceb01

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

TELEGRAM_CANCEL_FIX:
PASS

CANCEL_ERROR_REDIRECT:
PASS

CANCEL_STATE_PRESERVED:
PASS

CANCEL_ISS_PRESERVED:
PASS

CANCEL_ISSUES_TOKEN:
NO

REFRESH_ROTATION_ATOMIC:
PASS

REFRESH_SINGLE_USE:
PASS

CONCURRENT_DOUBLE_REFRESH:
AT_MOST_ONE_SUCCESS

REVOCATION_VERSION_CHECK:
PASS

RUFF:
PASS

PYRIGHT:
PASS

DIFF_CHECK:
PASS

MCP_TESTS:
35 passed (tests/unit/wb_sky_mcp/test_mcp_read_interface.py)

TELEGRAM_TESTS:
54 passed (MCP cancel/start in the MCP file; client_bot start/channel/return 54)

AI_PACKAGE_TESTS:
136 passed (tests/unit/ai_package_v1)

MIGRATION_TESTS:
1 passed (tests/migrations/test_alembic_heads.py) plus MCP migration unit assertion in the MCP file

OPENSPEC:
PASS

LOCAL_PROTOCOL_EXERCISE:
PASS

PROTOCOL_REGRESSION:
NONE

TOOLS:
get_profile
list_shops
get_capabilities
get_ai_package

WRITE_TOOLS:
NONE

PRODUCT_CODE_CHANGED:
YES

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
NONE

FORMAL_SCENARIO_CERTIFICATION:
PENDING_PREDEPLOY

PREDEPLOY_HARDENING:
PASS

NEXT_GATE:
FORMAL_SCENARIO_CERTIFICATION

FINAL_STATUS:
PREDEPLOY_HARDENING_PASS
```
