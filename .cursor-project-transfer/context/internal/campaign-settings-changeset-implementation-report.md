---
cursor:
  subagentId: "bc-fec0e994-47b5-5444-a715-50af2fa4d241"
---

# CAMPAIGN_SETTINGS_CHANGESET_IMPLEMENTATION_REPORT

Implementation did not start. Adopted foundation reverify is red on strict Pyright and OpenSpec strict. No product files were edited. PR HEAD is unchanged.

```text
PR:
#449

PR_HEAD_PRE:
3613cab827c59d38a1a0a1fabf102f99b0dd7d77

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

FOUNDATION_REVERIFY:
FAIL

ADOPTION_GATE:
RESOLVED

ADOPTION_COMMIT:
2b9b4f1d2d7b7a8ccf931aa1cc1bf83713e6ce36

BASELINE_RECONCILIATION:
RESOLVED

CANONICAL_CHANGESET:
app/modules/wb_sky_control_plane/models/changeset.py::ChangeSetV1

SUPPORTED_OPERATION_TYPES:
campaign.set_budget_policy (SetBudgetPolicyOperation)
campaign.set_sales_policy (SetSalesPolicyOperation)
campaign.set_bid_control_policy (SetBidControlPolicyOperation)

STATE_TOKEN:
FAIL

EXPECTED_CURRENT_VALUE:
FAIL

NORMALIZATION_REUSE:
FAIL

CAPABILITY_TRI_STATE:
FAIL

UNKNOWN_FAIL_CLOSED:
FAIL

DOMAIN_VALIDATORS:
FAIL

ATOMIC_REJECTION:
FAIL

IDEMPOTENCY_CONTRACT:
FAIL

SEMANTIC_DIFF:
FAIL

NO_OP:
FAIL

OK:
FAIL

REJECTED:
FAIL

CAMPAIGN_RESOURCE_REF:
FAIL

FORBIDDEN_WRITERS_REACHABLE:
NO

WB_WRITES:
NONE

PG_SETTINGS_WRITES:
NONE

CH_WRITES:
NONE

APPLY_AUTHORITY:
NOT_IMPLEMENTED

TESTS:
PASS — poetry run pytest -m unit tests/unit/wb_sky_control_plane/ — 40 passed

RUFF:
PASS — ruff check app/modules/wb_sky_control_plane tests/unit/wb_sky_control_plane alembic_/versions/e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py

PYRIGHT:
FAIL — poetry run pyright-strict on the same adopted scope — 26 errors, 0 warnings

OPENSPEC:
FAIL — openspec validate campaign-settings-changeset-contract --type change --strict — valid:false. Single issue: WARNING spec.md ADDED "ChangeSetV1 envelope and state_token" requirement text >500 characters. poetry run check-openspec config contract PASS.

SCENARIO_CERTIFICATION:
NOT_RUN

DIFF_CHECK:
PASS — git diff --check (clean worktree at PR HEAD)

COMMIT(S):
NONE

PR_HEAD_POST:
3613cab827c59d38a1a0a1fabf102f99b0dd7d77

PR_STATE:
DRAFT

FINAL_STATUS:
BLOCKED

BLOCKER:
FOUNDATION_REVERIFY_RED before product write.
1) pyright-strict adopted scope: 26 errors.
   - app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py:92,97,100 reportUnknownVariableType/reportUnknownMemberType (adverts_raw/get/item)
   - app/modules/wb_sky_control_plane/kernel/canonical_json.py:19,21 reportUnknownVariableType (item)
   - app/modules/wb_sky_control_plane/read/normalizer.py:107,109,140,143 reportUnknownVariableType/reportUnknownMemberType (nm_raw/get/settings/placements_map)
   - tests/unit/wb_sky_control_plane/test_a1_safety_regression.py:110 reportArgumentType (_RecordingWbReader vs WbPromotionV2ReadPort)
   - tests/unit/wb_sky_control_plane/test_changeset_contract.py:25 reportCallIssue/reportArgumentType (dict.update)
   - tests/unit/wb_sky_control_plane/test_normalizer_strict_boundary.py:65,72,103,113 reportUnknownVariableType/reportUnknownArgumentType
   - tests/unit/wb_sky_control_plane/test_pipeline_dry_run.py:107,163 reportArgumentType (_FakeWbReader vs WbPromotionV2ReadPort)
   - tests/unit/wb_sky_control_plane/test_semantic_digest_and_state_token.py:34,42 reportUnusedImport; :68,:69,:70 reportArgumentType
2) openspec validate --type change --strict: valid false, WARNING requirement text >500 characters on ChangeSetV1 envelope and state_token.
Product validation/dry-run extension was not started. tasks.md still textually says LOCAL_FOUNDATION_ADOPTION_REQUIRED is open; repository commits 2b9b4f1d2 and 7fdf5e002 already satisfy that gate. Task text was not edited because the reverify stop is before any write.
```
