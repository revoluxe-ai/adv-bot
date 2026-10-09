# Scenario coverage plan

CHANGE_ID: campaign-settings-changeset-contract
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: 4ad4932e9ae9d0600c915add3898d2e9c003c7e5c1f68f1a16b2f3c9dfd28d25
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true

This is derived planning evidence only. It defines required evidence; it does not assert that tests exist or PASS.

## GENERATED_FROM

PLAN_EVIDENCE_ID is sha256 of the UTF-8 LF blob below, including the final newline:

```text
campaign-settings-changeset-contract
plan
design.md:45b6e63b3efd507f6a921f2a306ea04e60907f10af3efc86fa98ec765f722cea
specs/campaign-settings-changeset-contract/spec.md:caa93914d7feec28f436123f1bcbea38e99530059806e39713407747e09aad9f
owner-contract.md:cb23940e598d9075574ed163f9e1793e78c2ea870d02e3635cffaa5c310f242b
lifecycle:design.md:45b6e63b3efd507f6a921f2a306ea04e60907f10af3efc86fa98ec765f722cea
```

INPUTS:
- DESIGN_REVISION: design.md content_hash 45b6e63b3efd507f6a921f2a306ea04e60907f10af3efc86fa98ec765f722cea
- SPEC_REVISION: specs/campaign-settings-changeset-contract/spec.md content_hash caa93914d7feec28f436123f1bcbea38e99530059806e39713407747e09aad9f
- OWNER_CONTRACT_REVISION: owner-contract.md content_hash cb23940e598d9075574ed163f9e1793e78c2ea870d02e3635cffaa5c310f242b
- LIFECYCLE_REVISION: design.md content_hash 45b6e63b3efd507f6a921f2a306ea04e60907f10af3efc86fa98ec765f722cea

## LIFECYCLE_COVERAGE

- L1: envelope, state_token, duplicate operation id, duplicate changeset id conflict, identical replay.
- L2: CampaignResourceRef / cmp_*, registry, normalization, domain, capability.
- L3: expected_current_value under state_token; missing/stale token.
- L4: atomic `NO_OP`, `OK`, or `REJECTED`.
- L5: no production writer on any status.

LIFECYCLE_GAPS: none
SPEC_SCENARIO_MISSING: none
PLANNING_LIFECYCLE_GAP: none
UNRESOLVED_PRODUCT_SEMANTICS: none

## Steady-state / already-true reconcile

STEADY_STATE_RECONCILE: present

`No semantic change is NO_OP` is the already-true case: the snapshot at `state_token` already matches normalized requested values.

## Global evidence rules

RUNTIME_SCENARIO_SEAM: call real `validate_changeset` (wb_sky_control_plane) plus real registry `normalize_value` where applicable. Do not mock classification, normalization, atomic rejection, or diff status.

THIN_ENDS: none. Dry-run has no I/O. Forbidden-adapter assertions are call-boundary spies (WB, PostgreSQL write, ClickHouse, `apply_adv_excel_rows`, shop-runner, MIXED `campaigns_info_v2/adapter.py`).

PROVIDER_RECEIPTS: not required. mode=plan does not execute tests.

PRODUCTION_ENTRYPOINT: `app.modules.wb_sky_control_plane.kernel.validate.validate_changeset` (extend existing; name from reconciliation doc).

## Rows

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Valid existing bounded operation produces OK
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope and state_token
  GIVEN_WHEN_THEN: GIVEN bounded op + matching state_token; WHEN validate_changeset; THEN OK with SemanticDiffEntryV1.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1-L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_valid_bounded_operation_ok
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Stale state_token is REJECTED
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope and state_token
  GIVEN_WHEN_THEN: GIVEN mismatched state_token; WHEN dry-run; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1 L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_stale_state_token
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Missing state_token is REJECTED
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope and state_token
  GIVEN_WHEN_THEN: GIVEN empty state_token; WHEN dry-run; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1 L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_missing_state_token
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate changeset id with a different body is REJECTED
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope and state_token
  GIVEN_WHEN_THEN: GIVEN prior record same id different hash; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_duplicate_changeset_id_conflict
  LIFECYCLE_STEPS: L1 L5
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Identical changeset id replay is deterministic
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope and state_token
  GIVEN_WHEN_THEN: GIVEN prior record same id same hash; WHEN validate; THEN same NO_OP or OK.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_duplicate_changeset_id_replay
  LIFECYCLE_STEPS: L1
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: cmp_star resource identity binds the diff
  REQUIREMENT_CONTEXT: CampaignResourceRef identity
  GIVEN_WHEN_THEN: GIVEN cmp_* registry row; WHEN validate; THEN diff binds CampaignResourceRef.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_cmp_resource_identity
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unresolved CampaignResourceRef is REJECTED
  REQUIREMENT_CONTEXT: CampaignResourceRef identity
  GIVEN_WHEN_THEN: GIVEN unknown ref; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_unresolved_resource_ref
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate operation id rejects the changeset
  REQUIREMENT_CONTEXT: CampaignResourceRef identity
  GIVEN_WHEN_THEN: GIVEN duplicate operation_id; WHEN structural validation; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_duplicate_operation_id
  LIFECYCLE_STEPS: L1
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unsupported mutation is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN unsupported op/field; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_unsupported_mutation
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Invalid value is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN out-of-domain value; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_invalid_value
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unknown capability is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN unknown capability token; WHEN capability step; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_unknown_capability
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unsupported capability tri-state is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN unsupported tri-state; WHEN capability step; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_unsupported_capability
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Normalization records requested and normalized values
  REQUIREMENT_CONTEXT: Validation pipeline and normalization
  GIVEN_WHEN_THEN: GIVEN form mismatch; WHEN validate; THEN OK with requested and normalized in SemanticDiffEntryV1.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L2 L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_normalization
  LIFECYCLE_STEPS: L2 L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: No semantic change is NO_OP
  REQUIREMENT_CONTEXT: Validation pipeline and normalization
  GIVEN_WHEN_THEN: GIVEN normalized match; WHEN validate; THEN NO_OP.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_no_op
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Deterministic diff for identical inputs
  REQUIREMENT_CONTEXT: Validation pipeline and normalization
  GIVEN_WHEN_THEN: GIVEN two identical invocations; WHEN validate twice; THEN equal status and diffs.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_deterministic_diff
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: expected_current_value mismatch is REJECTED
  REQUIREMENT_CONTEXT: Precondition under state_token
  GIVEN_WHEN_THEN: GIVEN valid token but stale expected_current_value; WHEN precondition; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_expected_current_mismatch
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Omitting expected_current_value does not bypass state_token
  REQUIREMENT_CONTEXT: Precondition under state_token
  GIVEN_WHEN_THEN: GIVEN omitted expected_current_value and bad state_token; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_omit_expected_does_not_bypass_token
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Multiple valid operations produce one OK
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN two valid ops; WHEN validate; THEN OK with both diffs.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_multiple_operations_ok
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Mixed valid and invalid operations reject the whole changeset
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN one valid one invalid; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_mixed_operations_atomic_reject
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate target mutation rejects the changeset
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN two ops same resource+field; WHEN validate; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L1 L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_duplicate_target_mutation
  LIFECYCLE_STEPS: L1 L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Validation result does not perform production writes
  REQUIREMENT_CONTEXT: No production write
  GIVEN_WHEN_THEN: GIVEN any terminal status; WHEN validate returns; THEN no forbidden adapter.
  PRODUCTION_ENTRYPOINT: validate_changeset
  CAUSAL_PATH: L5
  THIN_ENDS: spy only
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/wb_sky_control_plane/test_changeset_dry_run.py::test_no_production_write
  LIFECYCLE_STEPS: L5
  ROW_PLAN: required
