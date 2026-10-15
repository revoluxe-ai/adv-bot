---
cursor:
  subagentId: "bc-5e49c30a-b5a6-5442-9419-1bdefe8fb569"
---

# WB_SKY_MCP_READ_INTERFACE_INDEPENDENT_REVIEW_REPORT

```text
PR:
#452

REVIEW_HEAD:
c3c703d186ee31a4902f82fabc6677c6c3fd1353

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

PR_SCOPE_VALID:
YES

MCP_MODE:
READ_ONLY

CUSTOM_MCP_IMPLEMENTATION:
Hand-rolled Streamable HTTP subset in app/modules/wb_sky_mcp/http.py. Stateless POST /mcp, no Mcp-Session-Id, no SSE, no official mcp SDK. initialize/ping/tools/list/tools/call exist. notifications, protocol negotiation, protocol header, batch rejection, and invalid-token WWW-Authenticate do not match MCP 2025-11-25.

CUSTOM_MCP_SUBSET_SPEC_CONFORMANT:
NO

MCP_PROTOCOL_VERSION_REVIEWED:
2025-11-25 (stable, modelcontextprotocol.io/specification/2025-11-25). Draft 2026-07-28 was read and not used as the conformance target. The server hardcodes protocolVersion 2025-03-26.

CHATGPT_INTEROP_STATIC_REVIEW:
FAIL

OPENAI_DOCS_VERIFIED:
YES

CIMD_COMPATIBILITY:
FAIL

OAUTH_METADATA:
FAIL

AUTHORIZATION_RESPONSE_ISS:
FAIL

RESOURCE_BINDING:
PASS

PKCE_S256:
PASS

TELEGRAM_CONSENT_BOUNDARY:
PASS

DYNAMIC_SHOP_GRANTS:
PASS

CROSS_SHOP_ISOLATION:
PASS

ACCESS_TOKEN_VALIDATION:
PASS

IMMEDIATE_REVOCATION:
PASS

REFRESH_ROTATION:
PASS

REFRESH_REUSE:
PASS

REFRESH_CONCURRENCY:
GAP

READ_ONLY_BOUNDARY:
PASS

AI_PACKAGE_CANONICAL_REUSE:
PASS

OVERSIZE_SEMANTICS:
PASS

RATE_LIMIT:
NON_BLOCKING_GAP

MIGRATION:
PASS

PYRIGHT_CONFIG_WEAKENED:
NO

TEST_COVERAGE:
Unit tests cover the 21 scenario-plan rows against fakes. They do not cover the live CIMD document, notifications/initialized, protocol-version negotiation, invalid-token WWW-Authenticate, refresh races, or SqlConnectionRepository on PostgreSQL. Formal certify was not run.

FORMAL_SCENARIO_CERTIFICATION:
PENDING_PREDEPLOY

FINDINGS:

CRITICAL:
- CIMD reject of the live ChatGPT client. app/modules/wb_sky_mcp/cimd.py parse_client_metadata requires payload["token_endpoint_auth_method"] == "none". Fetched 2026-10-06, https://chatgpt.com/oauth/client.json publishes token_endpoint_auth_method "private_key_jwt" and token_endpoint_auth_methods_supported ["none", "private_key_jwt"]. OpenAI Authentication (developers.openai.com/plugins/build/auth, same date) says the plural field is the method set and the singular field is only a legacy preference. Intersection with this AS (metadata advertises only "none") is "none", but the server never gets there: authorize fails closed on the singular field. Required fix: accept the client when "none" is in token_endpoint_auth_methods_supported (or, if that array is absent, when the legacy field is "none"). Do not require the legacy field to be "none" when the array contains "none". Keep rejecting documents that offer only private_key_jwt, because this token endpoint does not verify ChatGPT's JWKS.

HIGH:
- notifications/initialized is answered. http.py mcp_endpoint treats every unknown method, including notifications with no id, as JSON-RPC -32601. MCP 2025-11-25: a notification MUST NOT get a response; Streamable HTTP MUST return 202 with an empty body. Required fix: if "id" is absent, accept notifications/initialized (and other notifications) with 202 and no body.
- Protocol version is not negotiated. initialize ignores params.protocolVersion and always returns "2025-03-26". MCP-Protocol-Version is ignored. Spec: an unsupported MCP-Protocol-Version MUST be HTTP 400. A client whose newest version is 2025-11-25 and that does not keep 2025-03-26 SHOULD disconnect. Required fix: accept the requested version when it is in a declared supported set (include 2025-11-25 if ChatGPT sends it), echo that version, and 400 an unsupported header.
- Invalid bearer does not challenge. Missing Authorization on POST /mcp returns 401 with WWW-Authenticate resource_metadata. A present but revoked, expired, or wrong-audience token on initialize/ping/tools/list returns 401 without WWW-Authenticate. tools/call catches McpError inside the method and returns HTTP 200 with isError, including UNAUTHENTICATED and AUTH_BACKEND_UNAVAILABLE. OpenAI: reject a bad token and send WWW-Authenticate so ChatGPT re-authorizes. Required fix: authentication and storage failures on /mcp return 401 or 503 with the same challenge header; do not wrap them as a successful tool result.
- iss is advertised and not returned on authorize errors. Metadata sets authorization_response_iss_parameter_supported true. OpenAI: set that flag only when every success and error authorization response includes exact iss. oauth_authorize returns local JSON for every McpError, including rate-limit after CIMD has already validated redirect_uri. Success and user-deny redirects from complete() do include iss, state, and the stored redirect. Required fix: once redirect_uri is validated, redirect errors with error, state, and iss. Keep JSON only when the redirect is not yet known.

MEDIUM:
- cancel_mcp discards the return URL. broker.cancel builds /oauth/complete?ticket= that would redirect access_denied with iss. bot_handlers.cancel_mcp stores that URL in _url and only sends cancel_text(). ChatGPT never sees the error callback.
- Refresh rotation is not transactional. _exchange_refresh loads the row, rotate_refresh mutates memory, then save() updates without SELECT FOR UPDATE. Two concurrent presentations of the same refresh can both pass the current-hash check and both issue 15-minute access tokens. The last commit wins. The loser refresh is neither current nor previous, so reuse detection does not revoke the connection. Sequential reuse of previous_refresh_token_hash does revoke and bumps authorization_version.
- Design timeouts (30s tools, 60s package) and the single logical-file fetch up to 2 MiB are not implemented. The 256 KiB / 1 MiB omission path is implemented and does not truncate.
- Rate limit is INCR then EXPIRE. A crash between them leaves a key with no TTL. client IP is request.client.host, not a trusted forwarded header. Authorize key is client_id|ip. ChatGPT shares one CIMD client_id and few egress IPs, so the 10/hour cap can become global. Auth still fails closed if Redis is down.
- mcpok:/mcpno: bypass channel, phone, and invite-gate middleware. mcpdc: and /chatgpt do not. An unsubscribed user can confirm and then be blocked from disconnect. Confirm still binds query.from_user to User.id and does not open other bot commands or another user's cabinets. Opening /start mcp_* only calls inspect_start.
- SqlConnectionRepository and SqlShopGrantReader have no PostgreSQL test. Memory repository and FakeRedis cover sequential GETDEL, TTL, and rotation. They do not prove row locks, timestamptz, or scalar_one_or_none on duplicate hashes.

LOW:
- git diff --check: app/modules/wb_sky_mcp/broker.py new blank line at EOF.
- ruff UP035 on alembic_/versions/a9c0e7b41d22_add_mcp_connection.py (typing.Sequence). MCP product modules are clean.
- MCP_TOKEN_SIGNING_SECRET has no minimum length. HS256 with algorithms=["HS256"] is appropriate for this combined authorization and resource server. alg=none is rejected.
- refresh_token_hash is indexed, not unique. previous hash is not indexed.
- Connection row does not store client_id. Any allowlisted chatgpt.com / chat.openai.com CIMD URL can present a stolen refresh. Possession of the refresh is still required.
- Integration edits (start handler, three middlewares, client_bot_run.py) are outside pyrightconfig_strict.json include. The PR only appends the MCP package and its tests. Rules, exclude, and prior include entries are unchanged.

INFO:
- Sessionless POST-only Streamable HTTP is legal in 2025-11-25: session id is MAY, SSE is optional when the response is application/json, GET/DELETE without a route are 405.
- Tool annotations and structuredContent are present. Unknown tool names stop before ExportService.
- Live CIMD redirect is https://chatgpt.com/connector_platform_oauth_redirect. Host allowlist chatgpt.com and chat.openai.com matches current OpenAI stable callback host. chat.openai.com is extra, not required by the live document.
- Default resource https://mcp.skyline.ru/mcp matches the requested stable endpoint when env is unset. MCP_ENABLED defaults false.
- MCP Inspector was not run. No local inspector session was invented.
- Tests fixture CIMD uses token_endpoint_auth_method "none", so they cannot catch the live document failure.

TESTS:
PASS. poetry run pytest tests/unit/wb_sky_mcp/test_mcp_read_interface.py tests/migrations/test_alembic_heads.py tests/client_bot/test_channel_subscription.py → 54 passed. poetry run pytest tests/unit/ai_package_v1 → 136 passed. Python 3.11.17. Inspector: NOT RUN.

RUFF:
FAIL. 1 error, UP035 in a9c0e7b41d22_add_mcp_connection.py. app/modules/wb_sky_mcp and tests/unit/wb_sky_mcp are clean.

PYRIGHT:
PASS for changed MCP scope. poetry run pyright -p pyrightconfig_strict.json app/modules/wb_sky_mcp tests/unit/wb_sky_mcp → 0 errors, using the Poetry 3.11 env. Full-repo pyright-strict was not re-run.

OPENSPEC:
PASS. poetry run check-openspec → OpenSpec config contract check passed. This command checks openspec/config.yaml only. Formal scenario certify was not run.

DIFF_CHECK:
FAIL. git diff --check origin/stage...c3c703d186ee31a4902f82fabc6677c6c3fd1353 reports a new blank line at EOF in app/modules/wb_sky_mcp/broker.py.

PRODUCT_CODE_CHANGED_BY_REVIEW:
NO

PRODUCTION_CONNECTIVITY:
NONE

PRODUCTION_WRITES:
NONE

MERGE_READINESS:
REPAIR_REQUIRED

FINAL_STATUS:
INDEPENDENT_REVIEW_REPAIR_REQUIRED
```

## Evidence notes

PR #452 head and origin/stage matched the expected SHAs after `git fetch origin`. Merge-base is `d2166b2d805b27a6656f46c6ccb8e56066b4e888`. Scope is the MCP change only (41 files).

Sources checked 2026-10-06:

- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/api/docs/mcp
- https://chatgpt.com/oauth/client.json
- https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

Shop grants: `SqlShopGrantReader.list_shops` filters `WBUserCabinet.user_id`, then `require_shop` uses exact string equality. `call_tool` calls `export_ai_package` only after `require_shop`. `shop_id` on `WBCabinet` is a string. Presenter calls `ExportService.export` and does not add SQL or a second coverage formula. Oversize files keep sha256 and size and set `OMITTED_OVER_BUDGET`.

Revocation: `disconnect` sets `revoked_at`, increments `authorization_version`, and clears the refresh hash. `authenticate` reloads the row and rejects a version mismatch or `revoked_at`. That makes a still-unexpired access token unusable on the next call.

Formal scenario certification: absence is a pre-deployment acceptance gate, not by itself the merge blocker. The merge blocker is the live CIMD mismatch and the protocol/auth-challenge gaps above. Do not treat unit PASS as `/opsx-spec-scenario-coverage mode=certify`.

Scenario plan `SCPV1-caabac3b666cb5d4` rows are mapped by the MCP unit tests (authorize, PKCE, consent, complete, refresh reuse, disconnect, shop grant, capabilities, package omission, Redis/PG fail-closed). Those tests use a CIMD fixture with `token_endpoint_auth_method: none`, not the live document.
