---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Slice B — stage integration + final CAS certification

Prior: [repair packet](./hierarchical-ad-control-settings-slice-b-repair-bc-787c8d26.md)

## RETURN

```
CHANGE: hierarchical-ad-control-settings
SLICE: B (final CAS + stage integration)
PRE_INTEGRATION_HEAD: 3dc03741922dc300bb539ae3aa5ace293f0863ba
INTEGRATED_STAGE: d5a41b7c5382cef91e64fe87c4e03b4b1cdc8f6c
CERTIFIED_HEAD: 0c8d25bef1d033219c9424503ba600b5351e2e64
PR: https://github.com/revoluxe-ai/adv-bot/pull/473
MERGE_TREE: ort merge origin/stage into branch (801c7058a) + CAS commit 0c8d25bef; clean

LOGICAL_SHOP_IDENTITY: (shop_id, feature_id)
LOGICAL_CAMPAIGN_IDENTITY: (shop_id, advert_id, feature_id)
INHERIT_STORAGE: row absent; campaign.clear_ad_control_feature
REVISION_MODEL: row.revision from ledger allocation on mutating ops
REVISION_SOURCE: AdControlSlotMutationLedger (PG INSERT ON CONFLICT DO UPDATE)
CLEAR_RECREATE_ABA_PROTECTION: CLEAR bumps ledger; recreate gets new revision/token != historical
SHOP_CREATE_CAS: absent + expected_revision=null; flush → RevisionConflictError on race
CAMPAIGN_CREATE_CAS: same
RAW_INTEGRITY_ERROR_EXPOSED: NO (translated at flush)
SHOP_NO_OP: semantic equality before UPDATE
CAMPAIGN_OVERRIDE_NO_OP: YES (before allocate/SQL)
CAMPAIGN_DISABLE_NO_OP: YES (before allocate/SQL)
NO_OP_WRITES_DB: NO for shop/campaign disable/override when unchanged
DRY_RUN_REPOSITORY_PARITY: validator NO_OP intents align with repository semantics

PRICE_SEMANTICS_COMPATIBILITY: Slice B OpenSpec references stage ADR drr-cpo-price-semantics (V1 order-value YES); no runtime CPO added
CATALOG_PRICE_BOUNDARY: CATALOG_PRICE_SEMANTICS_ACCEPTED = NO unchanged in docs

ALEMBIC_HEADS: stage multi-head + b1c2d3e4f5a7 off f9c0a1b2d3e4
MCP_TOPOLOGY_FOLLOWUP: rebuild #452 merge to include b1 after Slice B on stage (do not edit MCP in #473)

PG_INTEGRATION_TESTS: authored (16 cases); NOT_EXECUTED on cloud VM (missing test deps)
MIGRATION_TESTS: table/constraint checks in integration module
UNIT_TESTS: PASS 35
ADJACENCY_TESTS: Slice A in unit bundle
RUFF: NOT_RUN
PYRIGHT: NOT_RUN
OPENSPEC: docs updated; strict NOT_RUN on VM
OPSX_VERIFY: NOT_RUN
INDEPENDENT_REVIEW: NOT_RUN

UI: NO | RUNTIME_CPO: NO | WB_WRITES: NO | PRODUCTION_MIGRATION_APPLIED: NO | DEPLOY: NO | MERGE: NO

CRITICAL: —
HIGH: CI must run destructive_local PG integration + poetry gates + independent review
MEDIUM: MCP alembic merge after Slice B merge
LOW: —

FINAL_STATUS: BLOCKED_VERIFICATION (PG live + pyright/ruff/openspec/opsx/review pending)
```
