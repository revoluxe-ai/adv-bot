---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP — authorized PostgreSQL provider run

Change: `wb-sky-mcp-read-interface` (PR #452)  
Branch: `cursor/wb-sky-mcp-read-interface-127c` @ `fb5410ad2815e3529d55058d729ac6ac27dc84b0`

```text
WB_SKY_MCP_PG_AUTHORIZED_PROVIDER_RUN_REPORT

STATUS: PROVIDER_RUN_FAILED
AUTHORIZE_ONE_LIVE_RUN: consumed (one pytest process; exit 1)
LIVE_RUN: authorized_fail

SCENARIO_CERTIFY_PACKET_SOURCE: INDEPENDENT_REAUDIT block in internal/wb-sky-mcp-pg-independent-reaudit.md
  (formal SCENARIO_CERTIFY_PACKET in wb-sky-mcp-formal-scenario-certification.md stale: PROVIDER_TEST_IDS NONE_AUTHORED, wrong GAP_FILE_ID)

SCENARIO_CERTIFY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: INDEPENDENT_REAUDIT
  CHANGE_ID: wb-sky-mcp-read-interface
  WORKTREE_FINGERPRINT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
  ITEMS:
    - GAP_ID: wb-sky-mcp-read-interface::pg-sql-connection-repository::1
      GAP_FILE_ID: ac6c9f0b4939f81e
      DISPOSITION: CERTIFY
      KIND: PG
      CONTRACT_ID: wb_sky_mcp.connection_repository.pg_boundary.v1
      CONTRACT_SHA: 62f266181929e405063a06eb77d220eff97e178f50c7edea9d3e2477b3f2f64a
      TEST_CONTENT_SHA: aa2ffaa1059fd3e420cf437ae55d89696847fa1b246e5b2cbc8a95bf5c98b46e
      PRODUCTION_BOUNDARY_SHA: 31cd2828bc9c325b2f17d8552ec1c88e75a71aebc4a99214140b46d16495e123
      REQUIRED_EXECUTION_CLASS: destructive_local
    - GAP_ID: wb-sky-mcp-read-interface::pg-sql-shop-grant-reader::1
      GAP_FILE_ID: 6b0cb5efc25d18c2
      DISPOSITION: CERTIFY
      KIND: PG
      CONTRACT_ID: wb_sky_mcp.shop_grant.pg_boundary.v1
      CONTRACT_SHA: ed6c3daa0e13b6123a1005bce3b49408d16a818398d6d09d11298b46c225d074
      TEST_CONTENT_SHA: 8749d706eadee3138cbf8c9bb20ac4f4be146793c767833d194a56f36bd57dfe
      PRODUCTION_BOUNDARY_SHA: 9b59f782f0947baf78e2120bd04c4dac0d22ef6d5396f89d3d4ad29241386583
      REQUIRED_EXECUTION_CLASS: destructive_local

AUDITED_STATE_PREFLIGHT:
  HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0 PASS
  AUDITED_STATUS_SHA256: bce7e167f83c02688fd9c8770ccc29284328eb224e66480cb00ff9e3b0085912 PASS
  AUDITED_TRACKED_DIFF_SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 PASS
  AUDITED_UNTRACKED_MANIFEST_SHA256: d47476a1ff0070dc75f9eda5aed9cbe6c348c6a1ed27cbbf214d4e6cb17f0e95 PASS

ALLOWED_RUN_BLOCK_VERIFY:
  EXPECTED_ALLOWED_RUN_BLOCK_SHA256: dc15859a21b5518bdf71b40637842853623eaf25fed11860ba36dc3d0730a226
  COMPUTED_FROM_FROZEN_BLOCK_IN_REAUDIT_MD: 65529731494c55d68bbe7d1c03b2a1fa7f9548276f613990b97ec8b321c2675b
  VERDICT: MISMATCH (metadata vs fenced block text; git audited hashes still matched)
  PYTEST_STILL_RAN: yes (one-shot consumed per policy)

INFRA_PREP (non-audited, post-preflight):
  docker: not available (exit 127)
  postgres: local cluster 16/test_adv on 127.0.0.1:5433 with test_adv_bot_db created (pytest lifecycle still requires Docker compose preflight)

PYTEST_INVOCATION:
  poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local -vv --tb=short
  COLLECTED: 6
  PASSED: 0
  ERRORS: 6 (all setup_test_database → DOCKER_STAGE=detect)
  EXIT_CODE: 1

PROVIDER_EXECUTION_RECEIPTS:
  - .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/receipts/PROVIDER-ac6c9f0b4939f81e.md RESULT=ERROR
  - .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/receipts/PROVIDER-6b0cb5efc25d18c2.md RESULT=ERROR
  LOG_PATH: .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-20261006T165425Z.redacted.log
  LOG_SHA: 7eb95e03280cd734749270160e70ade7fe12a6d17af7ed57fe0e3e139e86e0ac

CONTRACT_CASE_MISMATCH: NO

WHAT_HAPPENED:
  Git audited-state preflight passed. Single authorized pytest process collected 6 provider tests but errored in session setup because destructive lifecycle requires Docker CLI/daemon for compose preflight; Cloud VM has no docker.

WHY:
  tests/conftest.py setup_test_database → destructive_lifecycle.ensure_resources → docker_preflight fails before PG schema bootstrap or provider test bodies.

CURRENT_STATE: authorization_spent; receipts record ERROR; not PROVIDER_EXECUTION_RECEIPT_READY

OWNER_DECISION_REQUIRED: true
  - Re-audit + new AUTHORIZE_ONE_LIVE_RUN on host with Docker (/opsx-test-env UP) or environment build that includes Docker + test compose.
  - Optional: fix ALLOWED_RUN_BLOCK_SHA256 drift in independent re-audit artifact.

NEXT_ACTION:
  /opsx-test-env UP (Docker) on capable host → independent re-audit → new AUTHORIZE_ONE_LIVE_RUN → re-invoke provider certify path

DO_NOT_DO_YET:
  - No retry pytest on this VM without fresh authorization
  - No /opsx-spec-scenario-coverage mode=certify PASS
  - No commit/push
```
