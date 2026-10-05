# Scenario coverage plan

CHANGE_ID: campaign-settings-changeset-contract
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: 495bd3ad403240413c2f26804814b941eb34d06c2b0db706aa36e102cea8cfee
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true

This is derived planning evidence only. It defines required evidence; it does not assert that tests exist or PASS.

## GENERATED_FROM

PLAN_EVIDENCE_ID is sha256 of the UTF-8 LF blob below, including the final newline:

```text
campaign-settings-changeset-contract
plan
design.md:c9242a6fd0defbdb3adf408f02a9eb0637755e0297e9215bca7bdcd97fafac08
specs/campaign-settings-changeset-contract/spec.md:bfc66402a1fe9d659226e8937de2bd8c7339d113b98da5cb8411dc8d77ee528b
owner-contract.md:315b194b566699849c15dcef1935718a1cc3972fd0b3642c118d758091f8bfcc
lifecycle:design.md:c9242a6fd0defbdb3adf408f02a9eb0637755e0297e9215bca7bdcd97fafac08
```

INPUTS:
- DESIGN_REVISION: design.md content_hash c9242a6fd0defbdb3adf408f02a9eb0637755e0297e9215bca7bdcd97fafac08
- SPEC_REVISION: specs/campaign-settings-changeset-contract/spec.md content_hash bfc66402a1fe9d659226e8937de2bd8c7339d113b98da5cb8411dc8d77ee528b
- OWNER_CONTRACT_REVISION: owner-contract.md content_hash 315b194b566699849c15dcef1935718a1cc3972fd0b3642c118d758091f8bfcc
- LIFECYCLE_REVISION: design.md content_hash c9242a6fd0defbdb3adf408f02a9eb0637755e0297e9215bca7bdcd97fafac08

## LIFECYCLE_COVERAGE

- L1: structural envelope, duplicate operation id, duplicate changeset id conflict, identical replay.
- L2: identity, Auto/Search separation, registry, normalization, domain, capability.
- L3: stale precondition and missing current snapshot.
- L4: atomic `NO_CHANGE`, `CHANGE`, or `REJECTED`.
- L5: no production writer on any status.

LIFECYCLE_GAPS: none
SPEC_SCENARIO_MISSING: none
PLANNING_LIFECYCLE_GAP: none
UNRESOLVED_PRODUCT_SEMANTICS: none

## Steady-state / already-true reconcile

STEADY_STATE_RECONCILE: present

`Normalized value equal to current is NO_CHANGE` is the already-true case: the snapshot already matches the requested normalized value, and the pure validator must not emit an actionable change.

## Global evidence rules

RUNTIME_SCENARIO_SEAM: call real `validate_changeset_v1` plus real registry `normalize_value`. Do not mock classification, normalization, atomic rejection, or diff status.

THIN_ENDS: none. The function has no I/O. Forbidden-adapter assertions are call-boundary spies proving WB, PostgreSQL write, ClickHouse, `apply_adv_excel_rows`, and shop-runner are not invoked.

PROVIDER_RECEIPTS: not required. mode=plan does not execute tests. PostgreSQL and ClickHouse are outside this change.

PRODUCTION_ENTRYPOINT: `app.modules.campaign_settings_contract.validate_changeset_v1` (name fixed by tasks.md).

## Rows

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Valid single-field change produces CHANGE
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope
  GIVEN_WHEN_THEN: GIVEN one mutable operation and a matching snapshot; WHEN validate runs; THEN status CHANGE with field, old_value, requested_value, normalized_value.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L1-L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_valid_single_field_change
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    UNIT_COMPONENT: optional
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate changeset id with a different body is REJECTED
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope
  GIVEN_WHEN_THEN: GIVEN prior record with same id and different hash; WHEN validate runs; THEN REJECTED conflict and no writer.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_duplicate_changeset_id_conflict
  LIFECYCLE_STEPS: L1 L5
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Identical changeset id replay is deterministic
  REQUIREMENT_CONTEXT: ChangeSetV1 envelope
  GIVEN_WHEN_THEN: GIVEN prior record with same id and same hash; WHEN validate runs; THEN same NO_CHANGE or CHANGE and no new persistence.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_duplicate_changeset_id_replay
  LIFECYCLE_STEPS: L1
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Auto and Search targets stay separate
  REQUIREMENT_CONTEXT: Operation target identity
  GIVEN_WHEN_THEN: GIVEN auto adv_id A and search adv_id K; WHEN Search operation validates; THEN old_value is the Search leg and A is not merged.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_auto_search_identity_separation
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unsupported campaign source or type is REJECTED
  REQUIREMENT_CONTEXT: Operation target identity
  GIVEN_WHEN_THEN: GIVEN an unregistered source or campaign type; WHEN validate runs; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_unsupported_campaign_type
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate operation id rejects the changeset
  REQUIREMENT_CONTEXT: Operation target identity
  GIVEN_WHEN_THEN: GIVEN two operations with one operation_id; WHEN structural validation runs; THEN REJECTED with no partial accept.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L1
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_duplicate_operation_id
  LIFECYCLE_STEPS: L1
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unsupported field is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN a field absent from registry and mutation_policy; WHEN validate runs; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_unsupported_field
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Read-only field is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN an identity, WB-fact, runtime, derived, technical, or unclassified setting field; WHEN validate runs; THEN REJECTED as not mutable.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_read_only_field
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Invalid value is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN a value outside normalization or allowed_values; WHEN validate runs; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_invalid_value
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Unknown capability is REJECTED
  REQUIREMENT_CONTEXT: mutation_policy extension
  GIVEN_WHEN_THEN: GIVEN an unknown capability token or a missing required grant; WHEN capability validation runs; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_unknown_capability
  LIFECYCLE_STEPS: L2
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Normalization records requested and normalized values
  REQUIREMENT_CONTEXT: Validation pipeline and normalization
  GIVEN_WHEN_THEN: GIVEN a requested form that normalizes to a different current value; WHEN validate runs; THEN CHANGE keeps requested_value and normalized_value.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L2 L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_normalization
  LIFECYCLE_STEPS: L2 L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Normalized value equal to current is NO_CHANGE
  REQUIREMENT_CONTEXT: Validation pipeline and normalization
  GIVEN_WHEN_THEN: GIVEN every operation already matches the snapshot after normalization; WHEN validate runs; THEN NO_CHANGE.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_no_op
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Multiple operations produce one atomic CHANGE
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN two valid operations on different fields; WHEN validate runs; THEN one CHANGE diff contains both fields.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_multiple_operations
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Mixed valid and invalid operations reject the whole changeset
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN one valid and one invalid operation; WHEN validate runs; THEN REJECTED and the valid operation is not actionable CHANGE.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_mixed_operations_atomic_reject
  LIFECYCLE_STEPS: L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Duplicate target field rejects the changeset
  REQUIREMENT_CONTEXT: Atomic ChangeSet
  GIVEN_WHEN_THEN: GIVEN two operation ids for the same target field; WHEN validate runs; THEN REJECTED.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L4
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_duplicate_target_field
  LIFECYCLE_STEPS: L1 L4
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Stale expected current value is REJECTED
  REQUIREMENT_CONTEXT: Precondition and missing state
  GIVEN_WHEN_THEN: GIVEN expected_current_value differs from the snapshot; WHEN precondition validation runs; THEN REJECTED as stale.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_stale_precondition
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Missing current state is REJECTED
  REQUIREMENT_CONTEXT: Precondition and missing state
  GIVEN_WHEN_THEN: GIVEN no snapshot for the target; WHEN validate runs; THEN REJECTED as missing current state.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L3
  THIN_ENDS: none
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_missing_current_state
  LIFECYCLE_STEPS: L3
  ROW_PLAN: required

SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md::#### Scenario: Validation result does not perform production writes
  REQUIREMENT_CONTEXT: No production write
  GIVEN_WHEN_THEN: GIVEN a result of CHANGE, NO_CHANGE, or REJECTED; WHEN validate returns; THEN no forbidden adapter is invoked.
  PRODUCTION_ENTRYPOINT: validate_changeset_v1
  CAUSAL_PATH: L5
  THIN_ENDS: spy only, no real writer
  REQUIRED_TESTS:
    SCENARIO_SEAM: tests/unit/campaign_settings_contract/test_changeset_v1.py::test_no_production_write
  LIFECYCLE_STEPS: L5
  ROW_PLAN: required
