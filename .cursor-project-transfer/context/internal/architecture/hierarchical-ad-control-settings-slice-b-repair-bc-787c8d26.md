---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Slice B architecture repair — certification packet

**PR:** [#473](https://github.com/revoluxe-ai/adv-bot/pull/473)  
**CERTIFIED_HEAD:** `3dc037419` (after repair; prior candidate `b7e44be6d` superseded)  
**START_STAGE:** `065509c111e96aff88255db479001b9c3da3a0d0`

## RETURN block

```
CHANGE: hierarchical-ad-control-settings
SLICE: B (architecture repair)
START_STAGE: 065509c111e96aff88255db479001b9c3da3a0d0
CERTIFIED_HEAD: 3dc037419
PR: https://github.com/revoluxe-ai/adv-bot/pull/473

LOGICAL_SHOP_IDENTITY: (shop_id, feature_id)
LOGICAL_CAMPAIGN_IDENTITY: (shop_id, advert_id, feature_id)
SCHEMA_VERSION_SEMANTICS: column on authoritative row; upgrade replaces slot; unsupported/newer fail closed

INHERIT_STORAGE: campaign row absent; resolver default INHERIT via context_loader
CLEAR_TO_INHERIT_OPERATION: campaign.clear_ad_control_feature

REVISION_MODEL: BIGINT monotonic per logical row; increments every successful mutation
STATE_TOKEN_ROLE: content fingerprint incl. revision; audit/diff only
ABSENT_PRECONDITION: expected_revision=null
CAS_WRITE_SEMANTICS: UPDATE/DELETE WHERE revision=expected; insert when absent + expected_revision=null
ABA_PROTECTION: revision never decreases; A→B→A yields revisions 1,2,3

IDEMPOTENCY_CONTRACT: bind_ad_control_idempotency → build_idempotency_fingerprint(semantic_digest, preview_digest); same key+digest replay via decide_idempotency
APPLY_AUTHORITY_BOUNDARY: dry-run only; no PG writes in validator; durable replay not runtime until Apply adapter slice
AUDIT_BOUNDARY: row metadata (revision, schema_version, updated_at, state_token); durable audit via existing Apply ledger; no campaign-settings-history duplicate

MIGRATION: b1c2d3e4f5a7_add_ad_control_settings_persistence.py
CURRENT_STAGE_ALEMBIC_HEADS: multiple (includes f9c0a1b2d3e4; stage at 065509c has no b1 yet)
SLICE_B_ALEMBIC_HEADS: b1c2d3e4f5a7 → down f9c0a1b2d3e4
MCP_CONCURRENT_TOPOLOGY: PR #452 branch merges 010e7ee6eac0 + f9c0a1b2d3e4 → 8de1846cff85 (parallel fork from f9)
EXPECTED_POST_SLICE_B_HEADS: b1c2d3e4f5a7 added as head off f9 until MCP rebases merge to include b1
REQUIRED_MCP_FOLLOWUP: rebuild merge head (010e7ee6eac0 + b1c2d3e4f5a7) before MCP V7 cert; do not edit MCP from Slice B

PG_INTEGRATION_TESTS: authored tests/integration/ad_control_settings/; VM run blocked (conftest aiofiles); run in CI/destructive_local PG
UNIT_TESTS: PASS 35 (python3 -m pytest -m unit --noconftest)
ADJACENCY_TESTS: Slice A unit suite included in 35
RUFF: NOT_RUN (poetry env unavailable on VM)
PYRIGHT: NOT_RUN (poetry env unavailable on VM)
OPENSPEC: updated; strict validate NOT_RUN on VM
OPSX_VERIFY: NOT_RUN
INDEPENDENT_REVIEW: NOT_RUN (Composer 2.5 pending)

UI: NO
WB_WRITES: NO
PRODUCTION_MIGRATION_APPLIED: NO
DEPLOY: NO
MERGE: NO

CRITICAL: none open in code after repair
HIGH: PG integration + pyright/ruff/openspec/opsx + independent review still required for full cert
MEDIUM: MCP alembic merge followup after Slice B merge
LOW: —

FINAL_STATUS: SLICE_B_READY_FOR_OWNER_REVIEW (verification gates partially pending on environment)
```
