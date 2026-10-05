# Scenario Coverage Plan

CHANGE_ID: ai-package-v1-contract
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-39d14fba55537e56
LIFECYCLE_STATUS: DERIVED

This is required-evidence planning only. It does not claim tests exist, were executed,
or passed. It does **not** assert apply gate PASS, archive GO, or scenario audit PASS.

## Lifecycle coverage

LIFECYCLE_COVERAGE (Derived Lifecycle L1–L9 from design.md; one Spec Scenario row each — no dedupe):

- L1 → S01 — input validation (shop_id, period bounds)
- L2 → S01, S02, S07, S08, S10, S23, S25 — shop scope via PgExportShopScopeReader (not bot_active warmup)
- L3 → S03, S04, S06, S07, S20, S22, S23 — CH `default_db.full_adv_wb_stat` campaign stat
- L4 → S03, S08, S09, S20 — CH `default_db.wb_common_stat` funnel (main_nmid only)
- L5 → S03, S10, S11, S14, S26 — PG minimal inventory / UNKNOWN (not detailed settings)
- L6 → S09, S12, S21 — shop orders/sales SOURCE_NOT_ASSIGNED
- L7 → S04, S13, S14, S15, S16, S22 — independent coverage dimensions (NO_DATA vs coverage)
- L8 → S17, S24 — manifest + sha256 determinism / hash integrity
- L9 → S05, S18, S19, S20, S24 — ZIP transport + validator

Steady-state / reconcile-on-deploy: **not_applicable** — v1 export is on-demand read/export;
invariants are proven per `ExportService.export` invocation (no periodic reconcile Spec required).

OPEN_QUESTIONS:

- PG `campaign_settings_snapshot` may ship as UNKNOWN until tasks §1.1–1.2 discovery; plan allows
  PARTIAL/UNKNOWN card while still requiring S10/S11/S26 evidence when seam is enabled.


## Architecture and evidence constraints

Architecture Decision References:

- `openspec/decisions/shop-data-source-strategy/decision.md`
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
- `openspec/decisions/clickhouse-sql-database-qualification/decision.md`
- `openspec/decisions/mode-defaults-policy-ownership/decision.md`
- Proposed: `openspec/changes/ai-package-v1-contract/decisions/ai-package-v1-exporter-ownership/decision.md`

Ownership & Placement (export read path):

- Export entry: `scripts/ai_package_v1_export.py` → `ExportService.export(shop_id, period)` (planned apply).
- PG shop scope: `PgExportShopScopeReader` via `get_async_session_maker(read_only=True)`;
  filter `WBCabinet.shop_id == shop_id`; inventory pattern `only_bot_active=False`
  (active_status != done). **Forbidden:** `postgres_provider` bot_active-only warmup,
  `WBShopDataManager` orchestrator, `_get_min_bids`, `backfill_min_bids_for_adv`,
  any `app/core/mp/wb/api` import/call on export path.
- CH reads: SQL text MUST qualify `default_db.full_adv_wb_stat` and
  `default_db.wb_common_stat`; campaign grain `adv_id` + `date`; Auto and Search
  ids remain separate rows (no silent merge).
- Funnel: `nmid IN ComplexAdv.main_nmid` set only; funnel `orders` MUST NOT feed
  shop product orders/sales card.
- PG inventory card (`campaign_settings_snapshot`): minimal relations only; NOT
  detailed field-level settings snapshot (deferred change).
- Missing shop orders source: `SOURCE_NOT_ASSIGNED` / `UNKNOWN` fail-closed; `NO_DATA`
  MUST NOT alone force incomplete `coverage`; no timestamp-only FULL coverage; no
  invented vendored WB API numeric limits.
- Manifest: per-file `sha256`, deterministic ordering; validator applies to domain
  contract independent of ZIP transport.
- Every behavioral Scenario: ≥1 `scenario_seam` through real export orchestration;
  thin ends stubbed only after causal boundary; stub parity requires boundary tests.
- PG/CH scenario flows that persist then read: separate WRITE vs READ integration ids
  when session modes differ (`sm(read_only=False)` write vs `sm(read_only=True)` pure read).


## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: ai-package-v1-contract
SOURCE_SPEC_SHA: a2869c4e6341958fdfb9fe9a6ebe473f854b989181d129dc9861881c26956632
PLAN_STATUS: ready
SCENARIOS_TOTAL: 26

## Apply traceability (design.md §2.2)

Authoritative mapped test ids for post-apply planning (does **not** claim execution PASS).
Evidence classes: `unit_seam` = causal unit/scenario-seam test; `integration_read` = live PG/CH
boundary test in `tests/integration/ai_package_v1/`.

| Id | Primary test(s) | Seam | Integration read |
|---|---|---|---|
| S01 | `test_export_with_scope_builds_manifest_and_payloads`, `test_validate_export_inputs_rejects_non_numeric_shop` | unit_seam | — |
| S02 | `test_shop_isolation_filters_foreign_shop`, `test_export_with_scope_builds_manifest_and_payloads` | unit_seam | — |
| S03 | `test_export_path_records_zero_wb_http_calls`, `test_ai_package_v1_has_no_forbidden_imports` | unit_seam | — |
| S04 | `test_empty_campaign_stat_not_full_coverage`, `test_empty_inventory_unknown_collection_none_coverage` | unit_seam | — |
| S05 | `test_export_service_zip_roundtrip_passes_validator`, `test_valid_golden_package_passes` | unit_seam | — |
| S06 | `test_campaign_stat_query_uses_default_db_qualification`, `test_ch_campaign_stat_reader_reads_live_full_adv_wb_stat` | unit_seam | integration_read (authored) |
| S07 | `test_auto_and_search_ids_preserved_separately`, `test_load_scope_preserves_auto_and_search_adv_ids` | unit_seam | — |
| S08 | `test_funnel_query_uses_default_db_and_nmids_param`, `test_ch_funnel_reader_reads_live_wb_common_stat` | unit_seam | integration_read (authored) |
| S09 | `test_funnel_orders_never_populate_shop_product_orders_card` | unit_seam | — |
| S10 | `test_pg_scope_queries`, `test_pg_export_shop_scope_reader_reads_live_inventory` | unit_seam | integration_read (authored) |
| S11 | `test_inventory_card_partial_coverage_not_full_wb_universe` | unit_seam | — |
| S12 | `test_shop_orders_sales_source_not_assigned` | unit_seam | — |
| S13 | `test_no_data_does_not_auto_force_partial_coverage`, `test_no_data_alone_leaves_coverage_unknown_not_partial` | unit_seam | — |
| S14 | `test_unknown_not_export_success`, `test_shop_orders_unknown_fail_closed` | unit_seam | — |
| S15 | `test_freshness_unknown_without_version`, `test_freshness_stale_when_version_before_period_end` | unit_seam | — |
| S16 | `test_export_manifest_has_no_fabricated_wb_api_limit_fields` | unit_seam | — |
| S17 | `test_manifest_hash_stable_across_builds`, `test_zip_build_twice_same_sha256_entries` | unit_seam | — |
| S18 | `test_valid_golden_package_passes` | unit_seam | — |
| S19 | `test_tampered_payload_fails_hash_mismatch` | unit_seam | — |
| S20 | `test_export_path_records_zero_wb_http_calls` | unit_seam | — |
| S21 | `test_shop_orders_sales_source_not_assigned` | unit_seam | — |
| S22 | `test_empty_campaign_stat_not_full_coverage` | unit_seam | — |
| S23 | `test_export_with_scope_builds_manifest_and_payloads` (9001/9002 rows) | unit_seam | — |
| S24 | `test_manifest_hash_stable_across_builds` | unit_seam | — |
| S25 | `test_shop_isolation_filters_foreign_shop` | unit_seam | — |
| S26 | `test_inventory_card_partial_coverage_not_full_wb_universe` | unit_seam | — |

Unit seam tests live under `tests/unit/ai_package_v1/` (authored; execution not certified in `mode=plan`).

### Boundary integration — authored, not executed (current snapshot)

File: `tests/integration/ai_package_v1/test_ch_pg_read_boundary.py` (`@pytest.mark.integration`,
`@pytest.mark.destructive_local`).

| Test id | Maps to | REQUIRED_EVIDENCE role |
|---|---|---|
| `test_ch_campaign_stat_reader_reads_live_full_adv_wb_stat` | S06 | `BOUNDARY_INTEGRATION_READ` (CH `default_db.full_adv_wb_stat`) |
| `test_ch_funnel_reader_reads_live_wb_common_stat` | S08 | `BOUNDARY_INTEGRATION_READ` (CH `default_db.wb_common_stat`) |
| `test_pg_export_shop_scope_reader_reads_live_inventory` | S10 | `BOUNDARY_INTEGRATION_READ` (PG `sm(read_only=True)` scope SELECT) |

`EXECUTION` (snapshot 2026-09-27): **NOT_EXECUTED** — pytest setup reported **3 ERROR** with Docker
Desktop daemon OFF / test compose unreachable. **Integration PASS is not claimed**; certify path
requires green execution and fresh `PROVIDER_EXECUTION_RECEIPT` when PG/CH ends are mandatory.

Full end-to-end export with live CH+PG in one orchestration test remains **not claimed** (per design §2.2).

### S01 — Single shop bounded period

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Single shop bounded period`
LIFECYCLE_STEPS: L1, L2
GIVEN_WHEN_THEN: GIVEN shop S and period P; WHEN export runs; THEN scope and rows reference only S and dates within P (or gap metadata only).
PRODUCTION_ENTRYPOINT: ExportService.export(S, P) → scope reader + dataset readers + manifest.
CAUSAL_PATH: Validate inputs → resolve shop-scoped inventory → read CH slices for P → emit manifest scope fields.
THIN_ENDS: CH client transport; optional PG scope SELECT.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: export-bounded-shop-period seam; assert manifest shop_id, period bounds, no foreign shop rows.
  CONTRACT_CASES: AIPKG-SCOPE-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG scope read `sm(read_only=True)`; CH campaign/funnel SELECT contracts when fixtures used.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S02 — Shop isolation

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Shop isolation`
LIFECYCLE_STEPS: L2, L3, L4
GIVEN_WHEN_THEN: GIVEN S1 and S2 data; WHEN export for S1; THEN no S2 identifiers in rows/manifest.
PRODUCTION_ENTRYPOINT: ExportService.export(S1, P).
CAUSAL_PATH: Scope query filters shop_id → CH queries restricted to scoped adv_ids/main_nmids only.
THIN_ENDS: CH/PG read adapters.
DOCUMENTED_PAIRING: S25 contract test mirrors isolation assertions (paired; not deduped).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: shop-isolation seam with mixed-shop fixtures; assert absence of S2 shop_id/campaign ids.
  CONTRACT_CASES: AIPKG-ISOLATION-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG scope + CH reads prove shop filter in SQL/parameters.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S03 — No WB API on export path

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No WB API on export path`
LIFECYCLE_STEPS: L3, L4, L5
GIVEN_WHEN_THEN: GIVEN export invoked; WHEN datasets load; THEN zero WB HTTP/client/collector entrypoints on export path.
PRODUCTION_ENTRYPOINT: ExportService.export → readers (no WBShopDataManager).
CAUSAL_PATH: Orchestration uses PG/CH adapters only; guards/spies at module boundary.
THIN_ENDS: CH/PG network clients (real or test doubles after boundary).
DOCUMENTED_PAIRING: S20 Export spy (contract-tests spec) — same observable, separate spec authority.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-wb-export-path seam; spy/deny `app/core/mp/wb/api`; assert zero calls.
  CONTRACT_CASES: AIPKG-NO-WB-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: WB API stack deny contract (unit).
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S04 — Missing accumulation is explicit

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Missing accumulation is explicit`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN empty CH/PG slice for P; WHEN export completes; THEN collection_outcome/coverage/reason_codes reflect gap (not silent FULL).
PRODUCTION_ENTRYPOINT: ExportService.export with empty dataset fixtures.
CAUSAL_PATH: Readers return empty → coverage assembler sets explicit reason_codes.
THIN_ENDS: CH/PG read adapters.
DOCUMENTED_PAIRING: S22 empty campaign stat (contract test) — paired coverage proof.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: missing-accumulation-explicit seam; assert non-success coverage semantics.
  CONTRACT_CASES: AIPKG-NO-DATA-COVERAGE-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: CH empty SELECT + PG scope read contracts.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S05 — Same domain different transport

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Same domain different transport`
LIFECYCLE_STEPS: L9
GIVEN_WHEN_THEN: GIVEN identical manifest/payload bytes in two transports; WHEN validator runs; THEN identical validation outcome.
PRODUCTION_ENTRYPOINT: Package validator on domain manifest (ZIP vs raw file bundle).
CAUSAL_PATH: Validator parses manifest + hashes before transport-specific decode differences.
THIN_ENDS: ZIP encoder (stdlib) optional second transport fixture.
DOCUMENTED_PAIRING: S18 valid package passes shares validator entry (paired).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: domain-transport-independence seam; two encodings, one validator result.
  CONTRACT_CASES: AIPKG-TRANSPORT-PARITY-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: ZIP encode/decode boundary (stdlib) + validator entry.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S06 — Campaign date grain preserved

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Campaign date grain preserved`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: GIVEN CH rows for S campaigns; WHEN campaign stat exported; THEN each row keeps campaign_id+date; no fabricated nm breakdown.
PRODUCTION_ENTRYPOINT: ch_campaign_stat_reader → `default_db.full_adv_wb_stat`.
CAUSAL_PATH: SQL preserves adv_id+date grain; export rows mirror CH grain.
THIN_ENDS: ClickHouse client.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: campaign-date-grain seam; assert row keys and absence of fabricated nm splits.
  CONTRACT_CASES: AIPKG-CH-STAT-GRAIN-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: CH integration: qualified `default_db.full_adv_wb_stat` query shape.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S07 — Auto and Search remain separate original rows

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Auto and Search remain separate original rows`
LIFECYCLE_STEPS: L2, L3
GIVEN_WHEN_THEN: GIVEN ComplexAdv with distinct Auto/Search adv_ids; WHEN stat exported; THEN separate rows per id (no silent merge).
PRODUCTION_ENTRYPOINT: Scope metadata + campaign stat reader.
CAUSAL_PATH: Scope exposes both ids → CH query returns both → manifest lists separate campaign_id rows.
THIN_ENDS: CH client; PG scope read.
DOCUMENTED_PAIRING: S23 two campaign ids preserved (contract test) — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: auto-search-separate-rows seam; assert two campaign_id values present.
  CONTRACT_CASES: AIPKG-AUTO-SEARCH-GRAIN-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG scope read for both ids; CH read returns distinct adv_id rows.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S08 — Funnel limited to main nmid per ComplexAdv

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Funnel limited to main nmid per ComplexAdv`
LIFECYCLE_STEPS: L2, L4
GIVEN_WHEN_THEN: GIVEN main_nmid set for in-scope campaigns; WHEN funnel exported; THEN only those nmids included.
PRODUCTION_ENTRYPOINT: ch_funnel_reader → `default_db.wb_common_stat` with nmid filter.
CAUSAL_PATH: Scope computes main_nmids → SQL IN clause → rows filtered.
THIN_ENDS: ClickHouse client.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: funnel-main-nmid-only seam; assert excluded shop nmids absent.
  CONTRACT_CASES: AIPKG-FUNNEL-NMID-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: CH integration proves qualified SQL + nmid filter parameters.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S09 — Funnel orders are not shop product orders

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Funnel orders are not shop product orders`
LIFECYCLE_STEPS: L4, L6
GIVEN_WHEN_THEN: GIVEN funnel orders metrics exist; WHEN shop product orders/sales card emitted; THEN funnel orders do not populate that card.
PRODUCTION_ENTRYPOINT: Export assembler for `shop_product_orders_sales` vs funnel dataset.
CAUSAL_PATH: Separate dataset cards; shop orders card uses SOURCE_NOT_ASSIGNED only.
THIN_ENDS: none (in-process assembly).
DOCUMENTED_PAIRING: S21 orders sales unassigned — paired manifest assertions.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: funnel-not-shop-orders seam; assert shop orders card empty/unassigned while funnel card may have orders metric.
  CONTRACT_CASES: AIPKG-ORDERS-SEPARATION-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S10 — PG inventory is read-only minimal grain

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: PG inventory is read-only minimal grain`
LIFECYCLE_STEPS: L5
GIVEN_WHEN_THEN: GIVEN PG inventory enabled; WHEN export reads PG; THEN read_only session, no bot_active/mode side effects, minimal inventory rows only.
PRODUCTION_ENTRYPOINT: PgExportShopScopeReader / pg_snapshot_reader.
CAUSAL_PATH: SELECT-only ORM/query → inventory card rows (ids/relations).
THIN_ENDS: async PG session factory.
DOCUMENTED_PAIRING: S26 inventory card partial semantics — paired card-level proof.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: pg-inventory-readonly-minimal seam; assert read_only=True, no write APIs called.
  CONTRACT_CASES: AIPKG-PG-INV-READONLY-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG integration: `sm(read_only=True)` session + shop-scoped SELECT.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S11 — Detailed settings not implied by inventory card

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings not implied by inventory card`
LIFECYCLE_STEPS: L5
GIVEN_WHEN_THEN: GIVEN v1 export; WHEN manifest describes campaign_settings_snapshot; THEN no FULL detailed settings coverage claim.
PRODUCTION_ENTRYPOINT: Manifest builder for `campaign_settings_snapshot` card.
CAUSAL_PATH: Card metadata uses PARTIAL/UNKNOWN; omits detailed field export.
THIN_ENDS: none.
DOCUMENTED_PAIRING: S26 — paired; distinct spec headings (S10 seam vs S11 manifest semantics).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-detailed-settings-claim seam; assert coverage/reason_codes forbid FULL settings snapshot.
  CONTRACT_CASES: AIPKG-PG-NO-DETAILED-SETTINGS-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S12 — Explicit unassigned source

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Explicit unassigned source`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: WHEN shop product orders/sales materialized; THEN SOURCE_NOT_ASSIGNED or UNKNOWN; no supplier/funnel stand-in.
PRODUCTION_ENTRYPOINT: Shop orders/sales dataset assembler (metadata-only v1).
CAUSAL_PATH: Fixed v1 policy from shop-data-source-strategy → manifest source field.
THIN_ENDS: none.
DOCUMENTED_PAIRING: S21 — paired contract test.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: shop-orders-unassigned seam; assert source identity + zero supplier rows.
  CONTRACT_CASES: AIPKG-SOURCE-NOT-ASSIGNED-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S13 — NO_DATA without automatic incomplete coverage

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: NO_DATA without automatic incomplete coverage`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN reason_codes includes NO_DATA; WHEN coverage evaluated; THEN NO_DATA alone does not force incomplete coverage without separate evidence.
PRODUCTION_ENTRYPOINT: Coverage dimension assembler per dataset card.
CAUSAL_PATH: Independent fields collection_outcome/coverage/reason_codes/freshness.
THIN_ENDS: none.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-data-not-auto-incomplete seam; assert coverage may remain non-incomplete when rules allow.
  CONTRACT_CASES: AIPKG-NO-DATA-VS-COVERAGE-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S14 — UNKNOWN fail-closed

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: UNKNOWN fail-closed`
LIFECYCLE_STEPS: L5, L7
GIVEN_WHEN_THEN: GIVEN field UNKNOWN; WHEN consumer interprets success; THEN UNKNOWN not counted as success or FULL coverage.
PRODUCTION_ENTRYPOINT: Manifest/card fields with UNKNOWN outcomes (e.g., deferred PG snapshot).
CAUSAL_PATH: Assembler sets UNKNOWN → validator and export summary treat as non-success.
THIN_ENDS: none.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: unknown-fail-closed seam; assert package-level success flags exclude UNKNOWN-as-FULL.
  CONTRACT_CASES: AIPKG-UNKNOWN-FAIL-CLOSED-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S15 — No fake coverage from timestamps

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No fake coverage from timestamps`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN latest timestamp T but missing history in P; WHEN coverage computed; THEN no FULL period coverage from T alone.
PRODUCTION_ENTRYPOINT: freshness_reader optional signal + coverage assembler (must not equate to FULL).
CAUSAL_PATH: Freshness separated from coverage dimension.
THIN_ENDS: optional CH max(timestamp) read.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-fake-coverage-from-timestamp seam.
  CONTRACT_CASES: AIPKG-FRESHNESS-NOT-COVERAGE-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: CH freshness read contract if used.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S16 — No fabricated WB limits

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No fabricated WB limits`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: WHEN manifest describes collection windows; THEN no unverified vendored OpenAPI numeric limits as normative MUST windows.
PRODUCTION_ENTRYPOINT: Capabilities/metadata builder.
CAUSAL_PATH: Only PG-evidenced reason_codes; no invented limit constants.
THIN_ENDS: none.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: no-fabricated-wb-limits seam; assert manifest excludes invented numeric WB caps.
  CONTRACT_CASES: AIPKG-NO-FAB-LIMITS-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S17 — Deterministic sha256

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Deterministic sha256`
LIFECYCLE_STEPS: L8
GIVEN_WHEN_THEN: GIVEN identical inputs; WHEN export twice; THEN per-file sha256 and manifest hash match.
PRODUCTION_ENTRYPOINT: ExportService.export → manifest serializer (stable sort keys).
CAUSAL_PATH: Deterministic ordering/serialization → stable hashes.
THIN_ENDS: ZIP optional; filesystem bytes.
DOCUMENTED_PAIRING: S24 repeatable manifest — paired contract test.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: deterministic-sha256 seam with frozen fixtures + determinism_clock hook.
  CONTRACT_CASES: AIPKG-HASH-DETERMINISM-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S18 — Valid package passes

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Valid package passes`
LIFECYCLE_STEPS: L9
GIVEN_WHEN_THEN: GIVEN golden ZIP; WHEN validator runs; THEN pass with no errors.
PRODUCTION_ENTRYPOINT: Package validator parse+verify.
CAUSAL_PATH: Schema version + sha256 + required cards validated.
THIN_ENDS: filesystem read of golden archive.
DOCUMENTED_PAIRING: S05 transport parity — shared validator entry (paired).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: validator-golden-pass seam.
  CONTRACT_CASES: AIPKG-VAL-PASS-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S19 — Tampered payload fails

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Tampered payload fails`
LIFECYCLE_STEPS: L9
GIVEN_WHEN_THEN: GIVEN one payload byte changed; WHEN validator runs; THEN hash mismatch failure.
PRODUCTION_ENTRYPOINT: Package validator hash verification.
CAUSAL_PATH: sha256 compare detects tamper.
THIN_ENDS: golden ZIP fixture mutation.
DOCUMENTED_PAIRING: none
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: validator-tamper-fail seam.
  CONTRACT_CASES: AIPKG-VAL-TAMPER-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S20 — Export spy shows no WB calls

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Export spy shows no WB calls`
LIFECYCLE_STEPS: L3, L4, L5
GIVEN_WHEN_THEN: GIVEN WB layer spied/denied; WHEN export on test PG/CH; THEN zero WB API calls.
PRODUCTION_ENTRYPOINT: Contract test harness invoking ExportService.export.
CAUSAL_PATH: Same as S03 with contract-test spec authority.
THIN_ENDS: PG/CH test fixtures; WB deny spy.
DOCUMENTED_PAIRING: S03 — paired; both rows required (exporter + contract-tests specs).
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-no-wb-spy seam (test spec mandated).
  CONTRACT_CASES: AIPKG-CT-NO-WB-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG/CH fixture reads.
  BOUNDARY_INTEGRATION_OTHER: WB API deny/spy boundary.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S21 — Orders sales unassigned

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Orders sales unassigned`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: WHEN export completes; THEN shop orders/sales source NOT_ASSIGNED/UNKNOWN; no supplier rows.
PRODUCTION_ENTRYPOINT: Contract test export completion assertions.
CAUSAL_PATH: Same as S12 under contract-test requirement.
THIN_ENDS: PG/CH fixtures.
DOCUMENTED_PAIRING: S12 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-orders-unassigned seam.
  CONTRACT_CASES: AIPKG-CT-ORDERS-UNASSIGNED-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S22 — Empty campaign stat

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Empty campaign stat`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: GIVEN no full_adv_wb_stat rows for P; WHEN export completes; THEN dataset coverage not FULL without proof; reason_codes present.
PRODUCTION_ENTRYPOINT: Export with empty campaign CH fixture.
CAUSAL_PATH: Same as S04 under contract-test requirement.
THIN_ENDS: CH read adapter.
DOCUMENTED_PAIRING: S04 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-empty-campaign-stat seam.
  CONTRACT_CASES: AIPKG-CT-EMPTY-STAT-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: CH empty SELECT integration.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S23 — Two campaign ids preserved

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Two campaign ids preserved`
LIFECYCLE_STEPS: L2, L3
GIVEN_WHEN_THEN: GIVEN Auto A and Search K; WHEN stat exported; THEN both campaign_ids appear separately.
PRODUCTION_ENTRYPOINT: Contract test fixtures + export.
CAUSAL_PATH: Paired with S07.
THIN_ENDS: PG scope + CH stat read.
DOCUMENTED_PAIRING: S07 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-two-campaign-ids seam.
  CONTRACT_CASES: AIPKG-CT-AUTO-SEARCH-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG scope + CH stat read integrations.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S24 — Repeatable manifest

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Repeatable manifest`
LIFECYCLE_STEPS: L8, L9
GIVEN_WHEN_THEN: GIVEN frozen fixtures + fixed clock; WHEN export twice; THEN manifest sha256 entries identical.
PRODUCTION_ENTRYPOINT: ExportService.export twice + compare manifest hashes.
CAUSAL_PATH: Paired with S17 determinism requirement.
THIN_ENDS: determinism_clock test hook.
DOCUMENTED_PAIRING: S17 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-repeatable-manifest seam.
  CONTRACT_CASES: AIPKG-CT-REPEAT-MANIFEST-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: not_applicable
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S25 — Foreign shop excluded

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Foreign shop excluded`
LIFECYCLE_STEPS: L2
GIVEN_WHEN_THEN: GIVEN CH rows for S1 and S2; WHEN export for S1; THEN no S2 shop_id or S2-only campaign ids.
PRODUCTION_ENTRYPOINT: Contract test export for S1.
CAUSAL_PATH: Paired with S02 isolation.
THIN_ENDS: CH/PG fixtures.
DOCUMENTED_PAIRING: S02 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-foreign-shop-excluded seam.
  CONTRACT_CASES: AIPKG-CT-ISOLATION-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG scope + CH queries with shop filter.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

### S26 — Inventory card partial semantics

SCENARIO_ID: `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Inventory card partial semantics`
LIFECYCLE_STEPS: L5
GIVEN_WHEN_THEN: WHEN export completes with PG inventory or UNKNOWN; THEN no FULL detailed settings coverage; card metadata defers detailed snapshot change.
PRODUCTION_ENTRYPOINT: Manifest assertions on campaign_settings_snapshot card.
CAUSAL_PATH: Paired with S10/S11 exporter scenarios.
THIN_ENDS: none.
DOCUMENTED_PAIRING: S10, S11 — paired.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: contract-inventory-partial seam.
  CONTRACT_CASES: AIPKG-CT-PG-PARTIAL-001
  STUB_CONTRACT: required when CH/PG/WB thin ends stubbed in seam; shared golden/schema parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable
  BOUNDARY_INTEGRATION_READ: PG inventory read when materialized.
  BOUNDARY_INTEGRATION_OTHER: not_applicable
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: unit seams use fixtures/fakes; integration uses test PG/CH per testing-rules; no production credentials.
MOCKING_CONSTRAINTS: do not patch ExportService orchestration, coverage assembler, or scope SQL builder; deny/spy only thin transport ends after causal boundary.

## UNRESOLVED_GAPS

none (planning); implementation/test evidence gaps expected until `/opsx-test` and audit.

## GENERATED_FROM

- design.md: `f9fbb10fc3da8381252b4d53b545de0aff88f2a35804a2d4a746e1fb5700d5cf`
- owner-contract.md: `a696763d0f544777288c6824e5119dbb482d52e6d0a860c196091a789674a551`
- delta specs:
- openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md: `6531e49810361e604c1007b0ad5167335b419af06da2c9613d7f1b2d8df480cd`
- openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md: `621a2a3ca85e42a863f19eaaf50305e5b9e28c9c17ecc825bce3b53fe5078ef8`
- combined SOURCE_SPEC_SHA: `a2869c4e6341958fdfb9fe9a6ebe473f854b989181d129dc9861881c26956632`
- PRODUCER_COMMAND: `/opsx-spec-scenario-coverage mode=plan change=ai-package-v1-contract`

SOURCE_RESOLUTION:

- mode: exact_path via `openspec status --change ai-package-v1-contract --json`
- primary_path: `openspec/changes/ai-package-v1-contract/`
- fallback_used: false

EXECUTION_PREFLIGHT:

- tests: NOT_EXECUTED (mode=plan)
- blocked_on_preflight: false
