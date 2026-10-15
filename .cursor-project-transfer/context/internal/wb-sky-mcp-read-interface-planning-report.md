---
cursor:
  subagentId: "bc-f6a47396-e829-57e1-815f-633a0fc4127c"
---

# WB Sky MCP read interface planning report

BASELINE_SHA: d2166b2d805b27a6656f46c6ccb8e56066b4e888
(fetch of origin/stage matched the expected SHA; stage did not move)

CHANGE: wb-sky-mcp-read-interface
Branch: cursor/wb-sky-mcp-read-interface-127c
Commit: 9eeb26407dbe0f4e7d1a9d5b639209cce9d1906a
PR: https://github.com/revoluxe-ai/adv-bot/pull/452 (draft, base stage)

MCP_MODE: READ_ONLY

V1_TOOLS:
get_profile
list_shops
get_capabilities
get_ai_package

CHANGESET_TOOLS: NONE
WRITE_TOOLS: NONE

TRANSPORT: Streamable HTTP on POST /mcp
SSE: not in V1

DEPLOYMENT_PLACEMENT: same FastAPI process as the client-bot webhook (`client_bot_run.py`). No new microservice. error-collector is not the host.

CANONICAL_READ_CONTRACT_REUSE: ExportService.export plus the existing family-gap catalog. MCP presenter does not define a second dataset contract. ZIP is not the MCP body.

CANONICAL_CHANGESET: not used. ChangeSetV1 is not copied. PR #449 is untouched.

AUTH_PROTOCOL: OAuth 2.1 Authorization Code + PKCE

USER_AUTH_UI: EXISTING_TELEGRAM_BOT

SEPARATE_LOGIN_WEBSITE: NO

AUTH_SERVER_PLACEMENT: first-party protocol routes on the same FastAPI app. No Auth0/Keycloak. email/password_hash exist on User and have no login routes.

TELEGRAM_ROLE: identity bootstrap, consent, disconnect

TELEGRAM_AS_BEARER_AUTH: NO

TELEGRAM_IDENTITY_MAPPING:
User.user_telegram_id (unique) → User.id principal.
WBUserCabinet (unique user_id + wb_cabinet_id) → WBCabinet.shop_id.
Message /start and create_user already create User. CommandStart does not read a deep-link payload today; that branch is designed, not implemented.
Published bot link: https://t.me/wb_adv_master_bot/

OAUTH_TRANSACTION_STORE:
Redis, 10 minute TTL, single-use consume for the transaction, return ticket, and authorization code. Existing Redis clients. Fail closed if Redis is down.
Durable ChatGPT connection and refresh-token hash: new PostgreSQL tables beside User (designed, migration not created).

ACCESS_TOKEN_PRINCIPAL: sub = User.id
ACCESS_TOKEN_TTL: 15 minutes
Claims: iss, sub, aud, exp, iat, scope, authorization_version, jti
No shop list in the token.

REFRESH_TOKEN_MODEL: 30 days, SHA-256 at rest, rotation, reuse of a revoked refresh revokes the connection.

SHOP_AUTHORIZATION: DYNAMIC_SERVER_SIDE
Every shop tool re-reads WBUserCabinet for that principal. Removal of the cabinet link denies the shop before access-token expiry.

TOKEN_SCOPE: wbsky:read

TELEGRAM_DEEPLINK_FLOW:
ChatGPT calls GET /oauth/authorize (PKCE S256, exact redirect_uri, scope wbsky:read only).
Server stores the transaction and returns a minimal page or technical redirect whose only action is https://t.me/wb_adv_master_bot?start=mcp_<txn>.
Opening the link is not consent.
User confirms in the bot. Principal resolves from from_user.id. If no User row, the existing create_user path runs, then the confirm button is still required.
Bot sends /oauth/complete?ticket=...
Complete consumes the ticket and 302s to the saved redirect_uri with code and the original state.
Token endpoint checks PKCE and issues the access token.
The start payload, ticket, and code are high-entropy, single-use, short TTL, bound to client/redirect/state, and are not MCP credentials.

DISCONNECT_FLOW:
Bot controls (wording is an implementation detail): Connect ChatGPT (explains that the OAuth start is in ChatGPT; it does not mint a bearer), Active ChatGPT connections, Disconnect ChatGPT.
Disconnect sets revoked_at, increments authorization_version, and revokes refresh tokens.
The next MCP call fails even if the access token has not expired.
Disconnect does not delete the User or the cabinets.

GET_AI_PACKAGE_CONTRACT:
Both structured content and honest omission.
Always: manifest, dataset cards, GAP catalog, file descriptors (name, sha256, size).
Inline bytes only for text/JSON up to 256 KiB per file and 1 MiB total.
Larger files stay as descriptors with OMITTED_OVER_BUDGET.
One named payload may be fetched if it is at most 2 MiB; otherwise PAYLOAD_TOO_LARGE with hash and size.
No ZIP. No second semantics. GAP, PARTIAL, and UNKNOWN pass through.

GET_PROFILE_CONTRACT: principal id, username if present, scope wbsky:read, connection id, authorization_version. No bot token, WB token, password, or telegram id.

GET_CAPABILITIES_CONTRACT: dynamic for principal, shop, scope, and transport version. Lists the four read tools. Marks writes and ChangeSet unsupported. Unknown or ungranted shop fails closed.

LIST_SHOPS_CONTRACT: current WBCabinet.shop_id, WBUserCabinet.name, WBCabinet.active. Empty list is success.

FAIL_CLOSED_CASES:
unknown client, redirect_uri mismatch, missing PKCE S256, scope other than wbsky:read
expired or reused transaction, ticket, or code
deep link presented as bearer
missing from_user
unknown principal or shop grant
revoked connection or stale authorization_version
Redis unavailable on authorize/complete/code
PostgreSQL unavailable for principal, version, or cabinets
payload over the transport cap presented as a full inline package
auth or export timeout

SECURITY_RISKS:
confused deputy and shop_id tampering — checked against live grants
token, code, and approval-style replay — single use plus version
prompt injection via shop text — JSON envelope, no model instructions inside data
oversized package — hard caps
secret leakage — response allowlist; logs omit tokens
SSRF — redirect only to the registered redirect_uri
cross-shop reads — user_id and shop_id together
MCP annotations — all four tools read-only

RATE_LIMIT_MODEL:
authorize 10/hour per client and IP
token 30/hour per principal
tools 60/minute per principal
get_ai_package 6/hour per principal and shop
Redis outage fails closed

AUDIT_METADATA: correlation id, principal id, shop id, tool name, allow/deny, authorization_version. No tokens.

CHATGPT_CONNECTION_REQUIREMENTS:
public HTTPS /mcp
Streamable HTTP
OAuth authorization-server and protected-resource metadata on the same host
public client, PKCE S256, pre-registered exact redirect URI
scope wbsky:read

CONFLICTS_WITH_PR449: none. No ChangeSet schema and no control-plane files.
CONFLICTS_WITH_PR450: none. Package semantics stay with the exporter; this change does not edit that PR.

OWNER_DECISIONS_REQUIRED:
accept the two Proposed decisions before implementation
register the ChatGPT redirect URI before any endpoint
separate implementation GO
owner-contract review is still outstanding

IMPLEMENTATION_READY: NO
PRODUCT_CODE_CHANGED: NO
PRODUCTION_WRITES: NONE
FINAL_STATUS: PLANNING_READY

Process note: `poetry run python tools/openspec/openspec_guard.py --scenario opsx_ff --strict` failed before poetry was available; `python3` rerun returned FAIL because the opsx_ff command corpus is over the size limit (83874 chars, limit 80001). That failure is pre-existing and was not treated as a product block. Planning artifacts were still written.

```text
TASK_GENERATION_READINESS
SCENARIO_PLAN_EVIDENCE_ID: SCPV1-caabac3b666cb5d4
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
TASKS_STATUS: READY
```

Tasks remain gated by section 0. No apply.
