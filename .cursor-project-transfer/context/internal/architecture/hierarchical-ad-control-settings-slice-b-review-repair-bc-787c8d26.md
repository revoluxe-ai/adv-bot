---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Slice B — review repair certification

Prior: [final cert](./hierarchical-ad-control-settings-slice-b-final-cert-bc-787c8d26.md)

## RETURN

```
CHANGE: hierarchical-ad-control-settings
SLICE: B
PRE_REPAIR_HEAD: f92f7d676cd10d55011b265e8c99376b0ea95bc0
CERTIFIED_HEAD: 086f6a9bb8aafa4c05819e33b1078e6603fcfd7c
STAGE: d5a41b7c5382cef91e64fe87c4e03b4b1cdc8f6c
PR: https://github.com/revoluxe-ai/adv-bot/pull/473

DRY_RUN_REPOSITORY_PARITY: PASS (validate + classify_* + parity tests)
SHOP_SCHEMA_VERSION_NOOP_PARITY: PASS
CAMPAIGN_DISABLE_SCHEMA_VERSION_NOOP_PARITY: PASS
LOGICAL_SHOP_IDENTITY: (shop_id, feature_id)
LOGICAL_CAMPAIGN_IDENTITY: (shop_id, advert_id, feature_id)
SCHEMA_VERSION_SEMANTICS: attribute only; unsupported fail-closed
REVISION_CAS_AUTHORITY: expected_revision only
STATE_TOKEN_ROLE: fingerprint/diagnostics only
STATE_TOKEN_SPEC_CONFLICT: NO (spec amended to revision scenarios)

OPENSPEC_STRICT: PASS (npx @fission-ai/openspec@1.6.0 validate … --type change --strict)
PYRIGHT_STAGE_ERRORS: 14
PYRIGHT_CANDIDATE_ERRORS: 14
PYRIGHT_DELTA: 0
PYRIGHT_CHANGED_SCOPE: BASELINE_DELTA_PASS

OPSX_STAGE: FAIL (openspec_guard opsx_verify: 125878 chars vs baseline 78307)
OPSX_CANDIDATE: FAIL (identical to stage — not introduced by Slice B)
OPSX_VERIFY: FAIL (pre-existing workflow artifact budget; no waiver)

UNIT_TESTS: PASS (45 Slice B focused incl. 10 parity)
PG_INTEGRATION_TESTS: PASS (CI migration-ephemeral-pg, 20 tests)
MIGRATION_TESTS: PASS (28 passed, 1 skipped)
SLICE_A_ADJACENCY: PASS (8)
PRODUCT_CONTROL_ADJACENCY: PASS (in adjacency set)
CHANGESET_APPLY_ADJACENCY: PASS
RUFF: PASS

GITHUB_MIGRATION_STATIC: SUCCESS (run 37978979009)
GITHUB_MIGRATION_EPHEMERAL_PG: SUCCESS (run 37978979009)

INDEPENDENT_REVIEW: Composer 2.5 @ 086f6a9bb — no CRITICAL/HIGH/MEDIUM on code
REVIEW_FINDINGS: LOW only (opsx guard pre-existing; PG not rerun locally)

ALEMBIC_HEAD: b1c2d3e4f5a7
ALEMBIC_HEAD_COUNT: 1

MCP_TOPOLOGY_FOLLOWUP: unchanged — MCP #452 after stage merge

UI: NO | RUNTIME_CPO: NO | WB_WRITES: NO | PRODUCTION_MIGRATION_APPLIED: NO | DEPLOY: NO | MERGE: NO

CRITICAL: —
HIGH: —
MEDIUM: — (repaired)
LOW: opsx_verify global guard baseline drift (stage == candidate)

FINAL_STATUS: BLOCKED_VERIFICATION (opsx_verify guard; pre-existing on stage)
```

Note: fix CERTIFIED_HEAD typo in coordinator copy — use `git rev-parse HEAD` → `086f6a9bb…` full SHA from git.
