---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Slice B — final certification (post migration gates)

Prior: [CI cert](./hierarchical-ad-control-settings-slice-b-ci-cert-bc-787c8d26.md)

## RETURN

```
CHANGE: hierarchical-ad-control-settings
SLICE: B
STAGE: d5a41b7c5382cef91e64fe87c4e03b4b1cdc8f6c (unchanged; compatible)
CERTIFIED_HEAD: f92f7d676cd10d55011b265e8c99376b0ea95bc0
PR: https://github.com/revoluxe-ai/adv-bot/pull/473

GITHUB_MIGRATION_STATIC: SUCCESS (run 37976504959)
GITHUB_MIGRATION_EPHEMERAL_PG: SUCCESS (run 37976504959; includes live PG suite)

PG_INTEGRATION_TESTS: PASS (CI: tests/ad_control_persistence_live --confcutdir=…)
PG_TEST_COUNT: 20
PG_RESULT: PASS

CLEAR_RECREATE_ABA: PASS (test_clear_recreate_aba_new_revision_and_token)
CONCURRENT_SHOP_CREATE: PASS (RevisionConflictError; test_concurrent_create_one_wins)
CONCURRENT_CAMPAIGN_CREATE: PASS (test_concurrent_campaign_create_one_wins)
RAW_INTEGRITY_ERROR_EXPOSED: NO (test_concurrent_create_does_not_leak_integrity_error)
NO_OP_ZERO_WRITE: PASS (override/disable/shop NO_OP + ledger test)
NO_OP_LEDGER_REVISION_CONSUMED: NO (test_no_op_does_not_consume_ledger_revision)
TRANSACTION_ROLLBACK_CONTRACT: PASS (repository docstring + test_flush_conflict_requires_rollback_before_reuse)

MIGRATION_TESTS: PASS (28 passed, 1 skipped)
UNIT_TESTS: PASS (35 Slice B focused)
SLICE_A_ADJACENCY: PASS (8 resolver/product unit)
PRODUCT_CONTROL_ADJACENCY: included in Slice A adjacency paths
CHANGESET_APPLY_ADJACENCY: PASS (changeset validate + idempotency contract units)

RUFF: PASS (ad-control paths)
PYRIGHT: FAIL (full pyright-strict: 95 errors repo-wide; includes ad_control_validate unknown-type reports)
OPENSPEC: FAIL (npx @fission-ai/openspec@1.6.0 validate … --strict: spec SHALL/MUST on price semantics requirement)
OPSX_VERIFY: FAIL (openspec_guard opsx_verify scenario baseline char budget)

INDEPENDENT_REVIEW: Composer 2.5 @ f92f7d676 — see findings below
REVIEW_FINDINGS:
  MEDIUM: DRY_RUN_REPOSITORY_PARITY (shop/campaign disable no-op vs repository)
  MEDIUM: OpenSpec identity drift (schema_version in spec vs implementation)
  MEDIUM: STATE_TOKEN_STALE spec scenario not implemented in V1 preconditions
  LOW: design op naming drift; duplicate live test paths; no semantic_digest unit tests

ALEMBIC_HEAD: b1c2d3e4f5a7
ALEMBIC_HEAD_COUNT: 1

MCP_TOPOLOGY_FOLLOWUP: After Slice B lands on stage, MCP #452 must integrate fresh stage, rebuild/repair Alembic merge topology including b1c2d3e4f5a7, then fresh V7 candidate/certification. Do not edit MCP #452 in Slice B.

UI: NO
RUNTIME_CPO: NO
WB_WRITES: NO
PRODUCTION_MIGRATION_APPLIED: NO
DEPLOY: NO
MERGE: NO

CRITICAL: —
HIGH: —
MEDIUM: dry-run/repository parity; OpenSpec strict + identity docs; STATE_TOKEN_STALE gap
LOW: design naming; duplicate test trees; semantic_digest tests

FINAL_STATUS: BLOCKED_REVIEW (certification-correctness MEDIUM); BLOCKED_VERIFICATION (pyright-strict full repo, OpenSpec strict, opsx_verify guard)
```

## CI wiring

- `.github/workflows/migration-gates.yml`: paths + `AD_CONTROL_PERSISTENCE_PG_URL` pytest step after Alembic upgrade.
- Fixture fix: `async_engine` function-scoped (pytest-asyncio ScopeMismatch).
