---
cursor:
  subagentId: "bc-2378a38d-e9fb-5d78-b8c6-1f23b2235bbc"
---

# WB_SKY_MCP_PROTOCOL_REREVIEW_REPORT

```text
PR:
#452

REVIEW_HEAD:
c2cb978a9eb3acab856c90dcd04b7b86accae11d

REPAIR_BASE:
c3c703d186ee31a4902f82fabc6677c6c3fd1353

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

LIVE_CHATGPT_CIMD_REVERIFIED:
YES

LIVE_CLIENT_AUTH_METHODS:
none
private_key_jwt

LIVE_CLIENT_LEGACY_PREFERENCE:
private_key_jwt

CIMD_REPAIR:
PASS

SELECTED_TOKEN_ENDPOINT_AUTH_METHOD:
none

INITIALIZE_NEGOTIATION_REPAIR:
PASS

NOTIFICATION_REPAIR:
PASS

AUTH_CHALLENGE_REPAIR:
PASS

WWW_AUTHENTICATE:
PASS

MCP_WWW_AUTHENTICATE_META:
PASS

TOOL_AUTH_METADATA_REPAIR:
PASS

AUTHORIZATION_ISS_REPAIR:
PASS

RESOURCE_BINDING:
PASS

PKCE_S256:
PASS

STREAMABLE_HTTP_REVIEW:
PASS

LOCAL_PROTOCOL_EXERCISE:
PASS

READ_ONLY_BOUNDARY:
PASS

TOOLS:
get_profile
list_shops
get_capabilities
get_ai_package

WRITE_TOOLS:
NONE

DYNAMIC_SHOP_GRANTS:
PASS

AI_PACKAGE_REUSE:
PASS

TESTS:
PASS. tests/unit/wb_sky_mcp/test_mcp_read_interface.py 31 passed. tests/migrations/test_alembic_heads.py 1 passed. Python 3.11.17. Root conftest skipped (--noconftest / --confcutdir) because this VM has no Poetry env; assertions were executed against the PR tree.

TELEGRAM_TESTS:
PASS for MCP start tests inside tests/unit/wb_sky_mcp (start payload, confirm binds user id, disabled start). tests/client_bot/test_channel_subscription.py did not collect in this partial environment (bot import chain). Repair diff does not touch that middleware.

AI_PACKAGE_TESTS:
PASS. tests/unit/ai_package_v1 136 passed (--confcutdir=tests/unit/ai_package_v1).

RUFF:
FAIL. ruff 0.9.10. app/modules/wb_sky_mcp and tests/unit/wb_sky_mcp clean. UP035 remains in alembic_/versions/a9c0e7b41d22_add_mcp_connection.py.

PYRIGHT:
FAIL for the full strict MCP scope in this environment. pyright 1.1.411, pyjwt 2.8.0: 10 reportUnknownMemberType on jwt.encode/decode and fakeredis dbsize. The five repaired modules (broker, cimd, errors, http, protocol) report 0 errors.

OPENSPEC:
PASS. python -m openspec.tools.check_openspec: OpenSpec config contract check passed.

DIFF_CHECK:
FAIL. git diff --check origin/stage...c2cb978 is broker.py:649 new blank line at EOF. The repair range c3c703d..c2cb978 is clean.

FORMAL_SCENARIO_CERTIFICATION:
PENDING_PREDEPLOY

CRITICAL:
NONE

HIGH:
NONE

MEDIUM:
- Telegram cancel still discards the OAuth error URL. bot_handlers.cancel_mcp stores broker.cancel() in _url and only sends cancel_text(). ChatGPT does not receive access_denied with iss from that button. Unchanged by this repair.
- Refresh rotation is still load, in-memory rotate_refresh, then save, without a row lock. Two concurrent presentations of the same refresh can both pass the current-hash check. Unchanged by this repair.

LOW:
- broker.py trailing blank line (git diff --check vs origin/stage).
- Alembic migration UP035 (typing.Sequence).
- Strict Pyright reports 10 library reportUnknownMemberType findings on jwt and fakeredis in this environment. Repaired modules are clean. Not a protocol defect.

PRODUCT_CODE_CHANGED_BY_REVIEW:
NO

PRODUCTION_CONNECTIVITY:
NONE

PRODUCTION_WRITES:
NONE

MERGE_READINESS:
READY_FOR_PREDEPLOY

FINAL_STATUS:
PROTOCOL_REREVIEW_PASS
```

## Binding

After `git fetch origin`, PR #452 head is `c2cb978a9eb3acab856c90dcd04b7b86accae11d` on `cursor/wb-sky-mcp-read-interface-127c`. It matches the expected SHA. `origin/stage` is `d2166b2d805b27a6656f46c6ccb8e56066b4e888`. Merge-base is that stage SHA. The repair commit is `fix(mcp): align ChatGPT OAuth and MCP lifecycle`. The main checkout stayed on `stage`. Review used a detached worktree.

## Live contracts (2026-10-06)

Fetched `https://chatgpt.com/oauth/client.json`:

- `token_endpoint_auth_method`: `private_key_jwt`
- `token_endpoint_auth_methods_supported`: `none`, `private_key_jwt`
- redirect: `https://chatgpt.com/connector_platform_oauth_redirect`
- grants: `authorization_code`, `refresh_token`
- response type: `code`

OpenAI Authentication (`developers.openai.com/apps-sdk/build/auth`, same document as plugins/build/auth) says the plural field is the method set and the singular field is only a legacy preference. ChatGPT uses the preference when it is in the intersection; otherwise it uses another method in the intersection. This authorization server advertises only `none`, `S256`, and `authorization_response_iss_parameter_supported=true`. `iss` is required on every success and error authorization response, exact string match.

MCP conformance target for this server is `2025-03-26` (lifecycle + Streamable HTTP). A supported requested version must be echoed. Any other version must be answered with a version the server supports, not echoed. Notifications and client responses that the server accepts are HTTP 202 with an empty body. `MCP-Protocol-Version` absence means `2025-03-26`; an unsupported header is HTTP 400. Session id remains optional.

Tool-level OAuth UI needs `securitySchemes` plus `_meta["mcp/www_authenticate"]` containing an RFC WWW-Authenticate value with `error` and `error_description`. SEP-1489 and the OpenAI Apps SDK example use that header value without extra surrounding quotes. Unauthenticated HTTP requests also use a `401` `WWW-Authenticate` header with `resource_metadata`.

## Finding evidence

CIMD: `select_token_endpoint_auth_method` intersects the plural set with `{"none"}`. The live preference `private_key_jwt` is outside that intersection, so the selected method is `none`. A document that offers only `private_key_jwt` is still rejected. Local call on the fetched document shape returned `none`.

Initialize: `negotiate_protocol_version` requires a non-empty string `protocolVersion`, a capabilities object, and `clientInfo.name` / `version`. `2025-03-26` is echoed. `2025-11-25` and `2026-07-28` return `2025-03-26` and are not echoed. Missing or non-string version is JSON-RPC `-32602`. Local ASGI confirmed this.

Notifications: a body with `method` and no `id` is a notification. `notifications/initialized` and a generic notification return HTTP 202 and an empty body. A batch of only that notification does the same.

Auth: malformed, expired, revoked, and stale `authorization_version` tokens on `tools/call` are HTTP 401. `WWW-Authenticate` is `Bearer realm="wb-sky"` with `error`, `error_description`, and `resource_metadata="https://mcp.skyline.ru/.well-known/oauth-protected-resource"`. The same challenge is `_meta["mcp/www_authenticate"]`. A bad bearer on `initialize` is also HTTP 401 with that header. Business `SHOP_NOT_GRANTED` stays HTTP 200 `isError` without the challenge.

Tools: `tools/list` is exactly the four read tools. Each `securitySchemes` entry is `oauth2` with scope `wbsky:read` only.

Authorization `iss`: after CIMD validates the redirect, request errors redirect to that URI with `error`, the original `state`, and exact `iss`. An untrusted client stays HTTP 400 with no `Location`. `complete()` success and deny redirects include `code` or `access_denied`, `state`, and exact `iss`.

Resource and PKCE: authorize and token exchange still require the configured resource. PKCE accepts only `S256`.

Streamable HTTP under `2025-03-26`: `Accept` must list `application/json` and `text/event-stream` (else 406). Body media type must be `application/json` (else 415). Responses are `application/json`. No `Mcp-Session-Id`. GET `/mcp` is 405. `ping`, `tools/list`, and `tools/call` work. Unknown method is `-32601`. Invalid `tools/call` params are `-32602`. An unsupported `MCP-Protocol-Version` on a non-initialize request is HTTP 400.

Boundaries unchanged by the repair diff: read-only tools, `ExportService.export`, shop grants from `WBUserCabinet.user_id`, Telegram used for identity, consent, and disconnect.

Formal scenario certification was not run. No non-production provider in this review replaces it. It stays a gate before production enablement.
