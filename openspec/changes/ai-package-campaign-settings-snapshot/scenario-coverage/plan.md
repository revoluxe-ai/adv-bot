# Scenario Coverage Plan

CHANGE_ID: ai-package-campaign-settings-snapshot
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-c1eba84a1b0b8a1e
LIFECYCLE_STATUS: DERIVED

This is required-evidence planning only. It does not claim tests exist, were executed,
or passed. It does **not** assert apply gate PASS, archive GO, or scenario audit PASS.

## Lifecycle coverage

LIFECYCLE_COVERAGE (Derived Lifecycle L1–L7 from design.md; one Spec Scenario row each — no dedupe):

- L1 → S01 — validate export inputs (`shop_id`; point-in-time settings; period bounds gate scope only)
- L2 → S01, S02, S04, S14, S15, S19 — shop scope via read-only PG (`only_bot_active=False`, `active_status != done`)
- L3 → S03, S04, S17, S19 — project auto/search legs per `AdvSetting` anchor (no silent merge)
- L4 → S05, S06, S07, S10, S11, S19 — map PG columns with `authority_class` + `field_provenance`
- L5 → S06, S08, S10, S16 — mark OPEN/unmapped WB fields `UNKNOWN`/`UNSUPPORTED`; no live WB fetch
- L6 → S09, S10, S13, S14, S17, S18 — attach `snapshot_assembled_at` + four completeness dimensions per card
- L7 → S13, S14, S17, S20, S21 — emit domain JSON; manifest card references payload + `sha256`

Steady-state / reconcile-on-deploy: **not_applicable** — settings snapshot is on-demand read/export;
invariants are proven per assembler invocation (no periodic reconcile Spec required).

OPEN_QUESTIONS:

- OPEN-01: full WB authoritative leg fields beyond PG sync columns remain `UNKNOWN`/`PARTIAL_PG_WB_SYNC`
  in slice 1; plan allows PARTIAL coverage while requiring S10/S16 evidence.
- OPEN-02: LOCAL_POLICY allowlist finalized at apply discovery; plan requires S05/S07 provenance tests.

## Architecture and evidence constraints

Architecture Decision References:

- `openspec/decisions/shop-data-source-strategy/decision.md`
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`
- `openspec/decisions/mode-defaults-policy-ownership/decision.md`
- Proposed: `openspec/changes/ai-package-campaign-settings-snapshot/decisions/ai-package-campaign-settings-snapshot-ownership/decision.md`

Ownership & Placement (settings export read path):

- Domain contract: `CampaignSettingsSnapshotV1` under `app/modules/ai_package_v1/domain/`.
- PG shop scope: `PgExportShopScopeReader` via `get_async_session_maker(read_only=True)`;
  filter `WBCabinet.shop_id == shop_id`; inventory pattern `only_bot_active=False`
  (`active_status != done`). **Forbidden:** `WBShopDataManager`, `postgres_provider`
  bot_active-only warmup, `AdvSettingsSnapshotDTO` as export schema, any `app/core/mp/wb/api`
  import/call on export path.
- Assembler: `CampaignSettingsAssembler` projects PG columns with provenance; PG NULL → JSON null.
- Manifest card `campaign_settings_snapshot`: `detailed_settings_export: true`; four completeness
  dimensions independent; MUST NOT claim FULL WB cabinet universe.
- **Non-contract references (must not alias):** `CampaignResourceSnapshotV1` (A1),
  `AdvSettingsSnapshotDTO` (Redis tick).
- Every behavioral Scenario: ≥1 `scenario_seam` through assembler/reader orchestration;
  thin ends stubbed only after causal boundary; WB API deny/spy at module boundary.

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: ai-package-campaign-settings-snapshot
SOURCE_SPEC_SHA: f6c56b7af60aa41b890ebbc4633f48d0aa1d6b1f39089f893e34d737a36959ac
PLAN_STATUS: ready
SCENARIOS_TOTAL: 21

## Apply traceability (design.md Derived Lifecycle)

| Id | Primary test(s) | Seam |
|---|---|---|
| S01 | `test_payload_schema_is_campaign_settings_snapshot_v1` | unit_seam |
| S02 | `test_payload_not_adv_settings_snapshot_dto`, `test_scope_not_bot_active_only` | unit_seam |
| S03 | `test_auto_and_search_legs_distinguishable` | unit_seam |
| S04 | `test_primary_grain_adv_setting_id` | unit_seam |
| S05 | `test_local_policy_provenance_not_wb_authoritative` | unit_seam |
| S06 | `test_unsupported_field_explicit` | unit_seam |
| S07 | `test_null_pg_column_stays_null` | unit_seam |
| S08 | `test_unknown_wb_field_fail_closed` | unit_seam |
| S09 | `test_four_completeness_dimensions_independent` | unit_seam |
| S10 | `test_partial_pg_wb_sync_explicit` | unit_seam |
| S11 | `test_settings_export_zero_wb_api_calls` | unit_seam |
| S12 | `test_export_does_not_write_state` | unit_seam |
| S13 | `test_manifest_references_domain_payload` | unit_seam |
| S14 | `test_detailed_export_flag_true` | unit_seam |
| S15 | `test_pg_reader_read_only_session` | unit_seam |
| S16 | `test_no_full_detailed_claim_when_partial` | unit_seam |
| S17 | `test_detailed_contract_when_applied` | unit_seam |
| S18 | `test_inventory_partial_before_detailed` | unit_seam |
| S19 | `test_detailed_contract_golden_legs` | unit_seam |
| S20 | `test_settings_export_spy_no_wb_calls` | unit_seam |
| S21 | `test_payload_type_guard_non_aliasing` | unit_seam |

Unit seam tests live under `tests/unit/ai_package_v1/` (authored at apply; execution not certified in `mode=plan`).

### S01 — Export payload is not control-plane snapshot

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export payload is not control-plane snapshot`
LIFECYCLE_STEPS: L1, L2
GIVEN_WHEN_THEN: GIVEN export assembles detailed settings for shop S; WHEN domain payload serialized; THEN schema MUST be `CampaignSettingsSnapshotV1`; MUST NOT be `CampaignResourceSnapshotV1`.
PRODUCTION_ENTRYPOINT: `CampaignSettingsAssembler.assemble(shop_id)` → domain JSON.
CAUSAL_PATH: PG read → assemble records → serialize with schema_version.
THIN_ENDS: async PG session factory.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: non-aliasing-type-guard seam; assert root schema_version and absence of cmp_* primary grain.
  CONTRACT_CASES: AIPKG-CS-NON-A1-001
  STUB_CONTRACT: PG rows fixture; no A1 import on path.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: optional PG scope read integration (slice 2+).
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; no production credentials.
MOCKING_CONSTRAINTS: do not patch assembler provenance logic; stub PG session only after scope query boundary.

### S02 — Export payload is not Redis tick DTO

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export payload is not Redis tick DTO`
LIFECYCLE_STEPS: L2
GIVEN_WHEN_THEN: GIVEN Redis operational snapshot exists; WHEN AI export builds settings; THEN MUST NOT use `AdvSettingsSnapshotDTO` schema; MUST NOT inherit bot_active-only scope.
PRODUCTION_ENTRYPOINT: `PgExportShopScopeReader.load_inventory(shop_id)`.
CAUSAL_PATH: Scope query without bot_active filter → assembler payload shape ≠ Redis DTO.
THIN_ENDS: PG session.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: non-redis-dto seam; assert payload keys and scope filter semantics.
  CONTRACT_CASES: AIPKG-CS-NON-REDIS-001
  STUB_CONTRACT: mixed bot_active rows; export includes non-bot-active inventory.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams only in slice 1.
MOCKING_CONSTRAINTS: do not patch scope SQL builder.

### S03 — Auto and Search legs remain distinguishable

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Auto and Search legs remain distinguishable`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: GIVEN auto adv_id A and search_adv_id K; WHEN exported; THEN separate leg sections with distinct wb_adv_id values.
PRODUCTION_ENTRYPOINT: `CampaignSettingsAssembler` leg projection.
CAUSAL_PATH: AdvSetting.adv_id + search_adv_id → nested auto_leg/search_leg.
THIN_ENDS: PG fixture rows.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: leg-separation seam; assert A and K in distinct legs.
  CONTRACT_CASES: AIPKG-CS-LEGS-001
  STUB_CONTRACT: required for PG reader stub.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit fixtures with A/K ids.
MOCKING_CONSTRAINTS: do not merge legs in assembler.

### S04 — Primary grain uses adv_setting anchor

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Primary grain uses adv_setting anchor`
LIFECYCLE_STEPS: L2, L3
GIVEN_WHEN_THEN: WHEN consumer reads record keys; THEN each row includes shop_id and adv_setting_id; MUST NOT require cmp_* as primary key.
PRODUCTION_ENTRYPOINT: `CampaignSettingsSnapshotRecordV1` model validation.
CAUSAL_PATH: PG AdvSetting.id → record.adv_setting_id.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: grain-anchor seam.
  CONTRACT_CASES: AIPKG-CS-GRAIN-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S05 — Local policy not masquerading as WB state

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Local policy not masquerading as WB state`
LIFECYCLE_STEPS: L4
GIVEN_WHEN_THEN: GIVEN field exists only in local AdvSetting columns; WHEN exported; THEN provenance LOCAL_POLICY; MUST NOT be WB_AUTHORITATIVE.
PRODUCTION_ENTRYPOINT: Assembler field_provenance builder.
CAUSAL_PATH: Column classification map → provenance entries.
THIN_ENDS: PG row fixture.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: local-policy-provenance seam.
  CONTRACT_CASES: AIPKG-CS-LOCAL-001
  STUB_CONTRACT: PG AdvSetting with budget/bot flags.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: do not patch authority_class map.

### S06 — Unsupported field slot stays explicit

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Unsupported field slot stays explicit`
LIFECYCLE_STEPS: L4, L5
GIVEN_WHEN_THEN: GIVEN contract field without safe reader in slice 1; WHEN export completes; THEN omitted or UNSUPPORTED with reason_codes; no fabricated default.
PRODUCTION_ENTRYPOINT: Assembler OPEN field slots (e.g. leg status beyond PG sync).
CAUSAL_PATH: UNSUPPORTED_FIELD reason_code on leg-level WB fields.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: unsupported-explicit seam.
  CONTRACT_CASES: AIPKG-CS-UNSUPPORTED-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S07 — Null PG column stays null

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Null PG column stays null`
LIFECYCLE_STEPS: L4
GIVEN_WHEN_THEN: GIVEN SQL NULL column; WHEN exported; THEN JSON null with provenance; no DTO/client defaults.
PRODUCTION_ENTRYPOINT: Assembler nullable field projection.
CAUSAL_PATH: PG None → export null + provenance (not bot_active=True default).
THIN_ENDS: PG fixture.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: null-stays-null seam.
  CONTRACT_CASES: AIPKG-CS-NULL-001
  STUB_CONTRACT: AdvSetting with null wb_bid_type / search_adv_id.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S08 — Unknown WB field fails closed for mutation eligibility

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Unknown WB field fails closed for mutation eligibility`
LIFECYCLE_STEPS: L5
GIVEN_WHEN_THEN: GIVEN required WB field UNKNOWN; WHEN consumer checks mutation eligibility; THEN disallowed; export MUST NOT mark authoritative success.
PRODUCTION_ENTRYPOINT: `CampaignSettingsSnapshotV1.is_mutation_eligible()` helper or provenance inspection.
CAUSAL_PATH: UNKNOWN authority_class on leg WB fields → fail-closed helper returns False.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: unknown-fail-closed seam.
  CONTRACT_CASES: AIPKG-CS-UNKNOWN-FC-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S09 — Four completeness dimensions stay independent

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Four completeness dimensions stay independent`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: WHEN card metadata read; THEN collection_outcome, coverage, reason_codes, freshness each present; fresh assembly MUST NOT alone imply FULL WB universe coverage.
PRODUCTION_ENTRYPOINT: Manifest card builder for campaign_settings_snapshot.
CAUSAL_PATH: Package-level + card-level completeness blocks assembled independently.
THIN_ENDS: determinism clock for snapshot_assembled_at.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: four-dimensions-independent seam.
  CONTRACT_CASES: AIPKG-CS-COMPLETE-4D-001
  STUB_CONTRACT: frozen clock fixture.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: do not patch completeness assembler shortcuts.

### S10 — Partial PG WB sync is explicit

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Partial PG WB sync is explicit`
LIFECYCLE_STEPS: L4, L5, L6
GIVEN_WHEN_THEN: GIVEN WB fields only partially in PG sync columns; WHEN export completes; THEN coverage PARTIAL; reason_codes include PARTIAL_PG_WB_SYNC; no FULL detailed WB claim.
PRODUCTION_ENTRYPOINT: Assembler package-level completeness.
CAUSAL_PATH: OPEN-01 disposition → PARTIAL coverage + reason_codes.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: partial-pg-wb-sync seam.
  CONTRACT_CASES: AIPKG-CS-PARTIAL-WB-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S11 — No WB API on settings export path

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: No WB API on settings export path`
LIFECYCLE_STEPS: L4, L5
GIVEN_WHEN_THEN: WHEN datasets loaded for settings snapshot; THEN zero WB HTTP/promotion adapter on export path.
PRODUCTION_ENTRYPOINT: `CampaignSettingsAssembler.assemble` with WB deny spy.
CAUSAL_PATH: PG-only readers; import guard on ai_package_v1 export subtree.
THIN_ENDS: PG session stub.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-wb-settings-path seam; spy/deny `app/core/mp/wb/api`.
  CONTRACT_CASES: AIPKG-CS-NO-WB-001
  STUB_CONTRACT: PG rows only.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: WB API deny contract.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: do not patch assembler orchestration; deny WB at import/call boundary.

### S12 — Export does not write operational state

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export does not write operational state`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN export completes; WHEN PG/Redis compared; THEN no settings/bot flags/snapshot keys changed.
PRODUCTION_ENTRYPOINT: Assembler with mocked session (no commit/flush).
CAUSAL_PATH: read_only session; assert no session.add/commit/execute DML.
THIN_ENDS: async session mock.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-write seam; session spy asserts SELECT-only pattern.
  CONTRACT_CASES: AIPKG-CS-NO-WRITE-001
  STUB_CONTRACT: AsyncSession mock with call tracking.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: stub session only; do not disable read path.

### S13 — Manifest references domain payload

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Manifest references domain payload`
LIFECYCLE_STEPS: L6, L7
GIVEN_WHEN_THEN: WHEN manifest describes campaign_settings_snapshot; THEN references logical payload file, schema version, hash.
PRODUCTION_ENTRYPOINT: `build_campaign_settings_snapshot_card`.
CAUSAL_PATH: Serialize payload → sha256 → card metadata.
THIN_ENDS: hash function (stdlib).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: manifest-payload-ref seam.
  CONTRACT_CASES: AIPKG-CS-MANIFEST-001
  STUB_CONTRACT: frozen payload bytes.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S14 — Detailed export flag distinguishes v1 inventory

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Detailed export flag distinguishes v1 inventory`
LIFECYCLE_STEPS: L6, L7
GIVEN_WHEN_THEN: WHEN detailed export enabled; THEN card MUST indicate detailed settings semantics; MUST NOT reuse minimal-only coverage claims.
PRODUCTION_ENTRYPOINT: Manifest card builder `detailed_settings_export: true`.
CAUSAL_PATH: Card flag + PARTIAL (not minimal-only) coverage semantics.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: detailed-flag seam.
  CONTRACT_CASES: AIPKG-CS-DETAILED-FLAG-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S15 — PG inventory is read-only minimal grain (exporter delta)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: PG inventory is read-only minimal grain`
LIFECYCLE_STEPS: L2
GIVEN_WHEN_THEN: WHEN export reads PG; THEN read_only session; no bot_active side effects; shop-scoped SELECT.
PRODUCTION_ENTRYPOINT: `PgExportShopScopeReader` / `PgCampaignSettingsReader`.
CAUSAL_PATH: get_async_session_maker(read_only=True) → SELECT join query.
THIN_ENDS: session factory injectable.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: pg-readonly-scope seam.
  CONTRACT_CASES: AIPKG-CS-PG-RO-001
  STUB_CONTRACT: session maker records read_only=True.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: optional slice 2+ PG integration.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit in slice 1.
MOCKING_CONSTRAINTS: do not patch SQL text builder.

### S16 — Detailed settings not implied by inventory card (exporter delta)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings not implied by inventory card`
LIFECYCLE_STEPS: L5, L6
GIVEN_WHEN_THEN: WHEN manifest describes card; THEN MUST NOT claim complete detailed WB coverage without contract; partial explicit.
PRODUCTION_ENTRYPOINT: Card metadata coverage field.
CAUSAL_PATH: PARTIAL coverage even when detailed_settings_export=true.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-false-full-detailed seam.
  CONTRACT_CASES: AIPKG-CS-NO-FALSE-FULL-001
  STUB_CONTRACT: not_applicable
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S17 — Detailed settings export uses dedicated contract (exporter delta)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings export uses dedicated contract when applied`
LIFECYCLE_STEPS: L3, L6, L7
GIVEN_WHEN_THEN: WHEN export materializes card; THEN CampaignSettingsSnapshotV1 payload; detailed flag; separate legs; not CampaignResourceSnapshotV1.
PRODUCTION_ENTRYPOINT: End-to-end assembler + card builder.
CAUSAL_PATH: Full slice 1 path integration in unit seam.
THIN_ENDS: PG stub.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: detailed-contract-applied seam.
  CONTRACT_CASES: AIPKG-CS-DETAILED-APPLIED-001
  STUB_CONTRACT: golden PG rows A/K.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: PG stub only.

### S18 — Inventory card partial semantics before detailed export (contract-tests delta)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Inventory card partial semantics before detailed export`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: GIVEN detailed not active (legacy fixture); WHEN export; THEN no FULL detailed coverage claim.
PRODUCTION_ENTRYPOINT: Contract test with `detailed_settings_export=false` fixture (regression guard).
CAUSAL_PATH: Baseline regression class LEGACY_BASELINE.
THIN_ENDS: static manifest fixture.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: legacy-partial-regression seam (optional static fixture).
  CONTRACT_CASES: AIPKG-CS-LEGACY-PARTIAL-001
  STUB_CONTRACT: minimal v1 manifest golden.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit static assertion.
MOCKING_CONSTRAINTS: none.

### S19 — Detailed settings contract tests when implemented (contract-tests delta)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Detailed settings contract tests when implemented`
LIFECYCLE_STEPS: L2, L3, L4
GIVEN_WHEN_THEN: GIVEN Auto A Search K; WHEN contract tests run; THEN CampaignSettingsSnapshotV1; separate legs; not A1/Redis DTO; explicit null/unknown.
PRODUCTION_ENTRYPOINT: Contract test golden fixture path.
CAUSAL_PATH: Paired with S03/S07/S21.
THIN_ENDS: PG fixture.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-detailed-golden seam.
  CONTRACT_CASES: AIPKG-CS-CT-GOLDEN-001
  STUB_CONTRACT: golden JSON fixture.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

### S20 — Settings export spy shows no WB calls (contract-tests ADDED)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Settings export spy shows no WB calls`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN WB layer spied; WHEN export builds detailed card; THEN zero WB API calls on settings path.
PRODUCTION_ENTRYPOINT: Contract test harness (paired with S11).
CAUSAL_PATH: Same as S11 under contract-tests spec authority.
THIN_ENDS: WB deny spy.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-no-wb-spy seam.
  CONTRACT_CASES: AIPKG-CS-CT-NO-WB-001
  STUB_CONTRACT: PG fixture.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: WB deny/spy.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: paired with S11; both required.

### S21 — Payload type guard (contract-tests ADDED)

SCENARIO_ID: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Payload type guard`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: WHEN validator parses domain JSON; THEN root schema CampaignSettingsSnapshotV1; MUST NOT validate as CampaignResourceSnapshotV1 or AdvSettingsSnapshotDTO.
PRODUCTION_ENTRYPOINT: Parse serialized payload + negative validation attempts.
CAUSAL_PATH: schema_version gate + Pydantic model_validate rejection of foreign shapes.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: payload-type-guard seam.
  CONTRACT_CASES: AIPKG-CS-CT-TYPE-GUARD-001
  STUB_CONTRACT: serialized bytes fixture.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit.
MOCKING_CONSTRAINTS: none.

## UNRESOLVED_GAPS

none (planning); implementation/test evidence gaps expected until apply and `/opsx-test`.

## GENERATED_FROM

- design.md: `4776ca00405b6f574667dea4800e8d2d13752a6defc57522b24787c5a7fb7777`
- owner-contract.md: `9a1ee013b90538079abdc133789b396686e4a02048da12068aa2ca9125e87d87`
- delta specs:
- openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md: `003bbdf8ef6f8b4ebec372cca5063d4a08a9daa5818bf9bb15511f2dbd8eb7fc`
- openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md: `158ab2030501a411587f44e6cef758ae127efd81de59ed12c4fab4222c876c6c`
- openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md: `4c44be22ad16b62334dbbac2d64659c10482348bf66d5d053682ab0925c98e5c`
- combined SOURCE_SPEC_SHA: `f6c56b7af60aa41b890ebbc4633f48d0aa1d6b1f39089f893e34d737a36959ac`
- PRODUCER_COMMAND: `/opsx-spec-scenario-coverage mode=plan change=ai-package-campaign-settings-snapshot`

SOURCE_RESOLUTION:

- mode: exact_path via bounded task `change=ai-package-campaign-settings-snapshot`
- primary_path: `openspec/changes/ai-package-campaign-settings-snapshot/`
- fallback_used: false

EXECUTION_PREFLIGHT:

- tests: NOT_EXECUTED (mode=plan)
- blocked_on_preflight: false
