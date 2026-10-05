# Design — ai-package-v1-contract

## Architecture Decision References

| Decision | Role in this change |
|---|---|
| `openspec/decisions/shop-data-source-strategy/decision.md` (Accepted) | Read PG/CH only; four completeness dimensions; open shop orders/sales; grain rules |
| `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` (Accepted) | Forbid funnel/ad/supplier stand-in for shop product orders/sales |
| `openspec/decisions/clickhouse-sql-database-qualification/decision.md` (Accepted) | New export CH SQL MUST use `default_db.<object>` in query text |
| `openspec/decisions/mode-defaults-policy-ownership/decision.md` (Accepted) | Export MUST NOT assign mode defaults or bot transitions |
| Proposed: `decisions/ai-package-v1-exporter-ownership/decision.md` | Module placement, read-only boundary, forbidden layers |

Canonical specs consumed (not modified): `openspec/specs/data-source-selection`,
`collection-modes`, `coverage-provenance`, `grain-preservation`.

## Ownership & Placement

| Concern | Owner | Layer | Notes |
|---|---|---|---|
| ZIP/domain manifest schema | This change (`ai-package-v1-exporter` spec) | Domain + transport | Independent of CH/PG layout |
| Dataset accumulation | Existing collectors / shop cycle | Out of scope | Export reads only |
| Campaign full stat read | Export read adapters | `app/modules/ai_package_v1/` (new) | Pattern from `full_wb_adv_stat.py` |
| Funnel/common read | Export read adapters | same | Filter `nmid IN main_nmids`; qualify `default_db` |
| Shop/campaign inventory for scope | `PgExportShopScopeReader` | `ai_package_v1/scope/` | `sm(read_only=True)` + join query; **no** `WBShopDataManager` |
| WB API | Forbidden on export path | — | Contract tests enforce |
| Entrypoint | Script/Job (read-only) | `scripts/ai_package_v1_export.py` (planned) | No TG/GUI in v1 slice |

Checklist:

- [x] Context-first decision lookup performed (`shop-data-source-strategy`, related Accepted).
- [x] Relevant decisions cited by path.
- [x] New decision proposed for exporter placement (registry gap: ZIP/format vs strategy).
- [x] Implementation layer matches decision (new read-only module, no collector ownership).

## Evidence — existing read patterns (repo)

**ClickHouse campaign full stat**

- `app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py`
  queries `default_db.full_adv_wb_stat` with `adv_id` + `date` grain (argMax/SUM
  patterns). Export SHOULD reuse query shapes or extract shared SQL under
  `ai_package_v1/sql/` with mandatory `default_db` qualification (even where legacy
  helpers in `common_stat_manager.py` omit DB prefix — export path MUST NOT copy
  unqualified SQL).

**ClickHouse common/funnel**

- `app/modules/shop_runner/wb_statistic_manager/backend/common_stat_manager.py`
  reads `wb_common_stat` by `nmid` + date range. Export MUST restrict `nmid` to
  `ComplexAdv.main_nmid` per in-scope campaign, not all shop articles.

**PostgreSQL shop/campaign scope (inventory — not warmup filter)**

- Models: `AdvSetting` (`models.py`) joined to `WBCabinet` (`wb_cabinet.py`) on
  `wb_cabinet_id`; scope key `WBCabinet.shop_id == shop_id`.
- Query evidence (inventory, **not** bot_active-only): static
  `WBShopDataManager.__get_advs(session, shop_id, only_bot_active=False)` —
  filters `active_status != 'done'`; `bot_active` filter applies only when
  `only_bot_active=True` (shop-runner default paths). Export scope MUST use
  `only_bot_active=False` and MUST NOT copy
  `postgres_provider.py` warmup filter (`bot_active.is_(True)`).
- Session evidence: `get_async_session_maker(read_only=True)` in
  `app/utils/db/session_maker.py` (same pattern as
  `WBShopDataManager._get_advs` parent, without instantiating manager).
- **Forbidden on export path:** import/call `WBShopDataManager` orchestrator,
  `_get_min_bids`, `backfill_min_bids_for_adv`, `WBDataManager`, `WBManager`, or
  any `app/core/mp/wb/api` entry.
- Named seam (apply): `PgExportShopScopeReader` builds in-process `ComplexAdv` /
  scope DTO from read-only ORM rows only.

**Coverage semantics (planning)**

- **PG inventory** = campaigns/relations returned by export scope query for the
  requested `shop_id` (partial by definition).
- **WB all-campaign universe** = not enumerated in v1 export; inventory MUST NOT
  be labeled FULL cabinet coverage.
- **CH datasets** = separate coverage dimensions per card (stat rows vs period).

**Auto vs Search campaign ids**

- `app/modules/shop_runner/service_manager/wb_shop_data_manager/dto/complex_adv/complex_adv.py`
  exposes `auto_adv_id`, `auction_adv_id` / `get_adv_id_by_type` — export MUST
  keep separate rows per id in campaign stat dataset (grain-preservation).

**Freshness (read-only signal, not coverage substitute)**

- `app/modules/shop_runner/service_manager/services/clickhouse_freshness_reader.py`
  may inform `freshness` field; MUST NOT set full `coverage` from max timestamp
  alone.

**Gaps (explicit UNKNOWN — no invented schema)**

- **Detailed** campaign/settings snapshot (full settings field export) — **out of
  v1**; candidate change `ai-package-campaign-settings-snapshot`. v1 MAY emit
  minimal inventory card or `UNKNOWN` until discovery §tasks 1.1–1.2 complete.
- Shop product orders/sales — permanently `SOURCE_NOT_ASSIGNED` in v1 per Owner
  contract and Accepted strategy.

## Semantic Write Target (read-path MEANING_LOCK)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
TARGET_ENTITY_OR_LEG: AI_PACKAGE_V1_READ_EXPORT — shop_id + bounded period → versioned domain manifest (+ ZIP transport)
ALLOWED_ADAPTERS:
  - CH: get_clickhouse_client + SQL text qualified default_db.full_adv_wb_stat (campaign+date)
  - CH: get_clickhouse_client + SQL text qualified default_db.wb_common_stat (nmid IN ComplexAdv.main_nmid set only)
  - PG: `PgExportShopScopeReader` via `get_async_session_maker(read_only=True)` +
    AdvSetting/WBCabinet join (inventory scope; no writes)
FORBIDDEN_ADAPTERS:
  - app/core/mp/wb/api and any WB HTTP collect path
  - `WBShopDataManager` orchestrator, `_get_min_bids`, `backfill_min_bids_for_adv`
  - supplier GET orders/sales (ORDERS_OR_SALES_REPORTS_READ) as shop product feed
  - wb_common_stat shop-wide or funnel orders as shop product orders/sales
  - shop-runner updaters, collectors, CommonSaleStatUpdater write path
  - snapshot_updater `postgres_provider` bot_active-only warmup filter as export scope
  - concatenate_stats-style silent Auto+Search merge without labeled derivative file
EVIDENCE:
  - openspec/decisions/shop-data-source-strategy/decision.md
  - paths listed in Evidence section above
OWNER_DECISION_SOURCE: owner-contract.md (REVIEWED; owner-contract-review PASS
  2026-09-27; D-001..D-005)
PAIRED_TESTS: specs/ai-package-v1-contract-tests/spec.md + exporter spec (26 source
  scenarios; traceability via authoritative `scenario-coverage/plan.receipt.json` —
  verify `SCENARIO_COUNT` and `INPUTS` hashes at gate, do not embed receipt id in
  design.md);
  contract tests MUST spy WB API, WBShopDataManager/min-bids, and CH `default_db.` SQL
```

## Derived Lifecycle

`LIFECYCLE_STATUS: DERIVED`

| Step | Transition | SOURCE |
|---|---|---|
| L1 | Validate inputs (`shop_id`, period bounds, timezone) | owner-contract.md; exporter spec |
| L2 | Resolve shop scope via `PgExportShopScopeReader` (inventory ids, main nmids) | PG evidence; grain-preservation; no WBShopDataManager |
| L3 | Read CH campaign stat for scoped `adv_id`s × P | full_wb_adv_stat patterns; CH qualification decision |
| L4 | Read CH funnel for scoped main nmids × P | common_stat_manager patterns + main_nmid rule |
| L5 | Materialize PG inventory card (minimal) or UNKNOWN; not detailed settings snapshot | tasks §1/§6; future `ai-package-campaign-settings-snapshot` |
| L6 | Emit shop orders/sales card as SOURCE_NOT_ASSIGNED | shop-data-source-strategy §10; owner-contract |
| L7 | Compute independent outcome/coverage/reason_codes/freshness per dataset | coverage-provenance spec |
| L8 | Serialize domain manifest + payloads; compute sha256 | exporter spec |
| L9 | Encode ZIP (transport); optional validator pass | contract-tests spec |

No material A|B branch unresolved at planning time.

## Spec scenario test traceability (apply §2.2)

Authoritative scenario ids: `scenario-coverage/plan.md` (S01–S26). Evidence
classes: `unit_seam` = causal ExportService/reader/validator unit test (pytest
green); `integration_read` = live test PG/CH boundary (`tests/integration/ai_package_v1/`);
`pending` = no causal test yet (audit must not treat as PASS).

| Id | Spec scenario (delta) | Primary test(s) | Seam | Integration read |
|---|---|---|---|---|
| S01 | Single shop bounded period | `test_export_with_scope_builds_manifest_and_payloads`, `test_validate_export_inputs_rejects_non_numeric_shop` | unit_seam | — |
| S02 | Shop isolation | `test_shop_isolation_filters_foreign_shop`, `test_export_with_scope_builds_manifest_and_payloads` | unit_seam | — |
| S03 | No WB API on export path | `test_export_path_records_zero_wb_http_calls`, `test_ai_package_v1_has_no_forbidden_imports` | unit_seam | — |
| S04 | Missing accumulation is explicit | `test_empty_campaign_stat_not_full_coverage`, `test_empty_inventory_unknown_collection_none_coverage` | unit_seam | — |
| S05 | Same domain different transport | `test_export_service_zip_roundtrip_passes_validator`, `test_valid_golden_package_passes` | unit_seam | — |
| S06 | Campaign date grain preserved | `test_campaign_stat_query_uses_default_db_qualification`, `test_ch_campaign_stat_reader_reads_live_full_adv_wb_stat` | unit_seam | integration_read |
| S07 | Auto and Search remain separate | `test_auto_and_search_ids_preserved_separately`, `test_load_scope_preserves_auto_and_search_adv_ids` | unit_seam | — |
| S08 | Funnel limited to main nmid | `test_funnel_query_uses_default_db_and_nmids_param`, `test_ch_funnel_reader_reads_live_wb_common_stat` | unit_seam | integration_read |
| S09 | Funnel orders are not shop product orders | `test_funnel_orders_never_populate_shop_product_orders_card` | unit_seam | — |
| S10 | PG inventory read-only minimal grain | `test_pg_scope_queries`, `test_pg_export_shop_scope_reader_reads_live_inventory` | unit_seam | integration_read |
| S11 | Detailed settings not implied | `test_inventory_card_partial_coverage_not_full_wb_universe` | unit_seam | — |
| S12 | Explicit unassigned source | `test_shop_orders_sales_source_not_assigned` | unit_seam | — |
| S13 | NO_DATA without automatic incomplete coverage | `test_no_data_does_not_auto_force_partial_coverage`, `test_no_data_alone_leaves_coverage_unknown_not_partial` | unit_seam | — |
| S14 | UNKNOWN fail-closed | `test_unknown_not_export_success`, `test_shop_orders_unknown_fail_closed` | unit_seam | — |
| S15 | No fake coverage from timestamps | `test_freshness_unknown_without_version`, `test_freshness_stale_when_version_before_period_end` | unit_seam | — |
| S16 | No fabricated WB limits | `test_export_manifest_has_no_fabricated_wb_api_limit_fields` | unit_seam | — |
| S17 | Deterministic sha256 | `test_manifest_hash_stable_across_builds`, `test_zip_build_twice_same_sha256_entries` | unit_seam | — |
| S18 | Valid package passes | `test_valid_golden_package_passes` | unit_seam | — |
| S19 | Tampered payload fails | `test_tampered_payload_fails_hash_mismatch` | unit_seam | — |
| S20 | Export spy shows no WB calls | `test_export_path_records_zero_wb_http_calls` | unit_seam | — |
| S21 | Orders sales unassigned | `test_shop_orders_sales_source_not_assigned` | unit_seam | — |
| S22 | Empty campaign stat | `test_empty_campaign_stat_not_full_coverage` | unit_seam | — |
| S23 | Two campaign ids preserved | `test_export_with_scope_builds_manifest_and_payloads` (9001/9002 rows) | unit_seam | — |
| S24 | Repeatable manifest | `test_manifest_hash_stable_across_builds` | unit_seam | — |
| S25 | Foreign shop excluded | `test_shop_isolation_filters_foreign_shop` | unit_seam | — |
| S26 | Inventory card partial semantics | `test_inventory_card_partial_coverage_not_full_wb_universe` | unit_seam | — |

Full end-to-end export orchestration with live CH+PG in one test is **not**
claimed; CH/PG proof is via reader boundary integration tests above. Those
integration tests are **authored**; green execution requires local Docker test
compose (`tests/docker-compose.test.yml`). Scenario audit/certify (`mode=audit`)
remains post-apply.

## Technical design

### Module layout (proposed — apply implements)

```
app/modules/ai_package_v1/
  domain/          # manifest schema, dataset ids, enums (SOURCE_NOT_ASSIGNED, coverage)
  scope/           # PgExportShopScopeReader (PG read-only inventory)
  readers/         # ch_campaign_stat_reader, ch_funnel_reader, pg_snapshot_reader
  export/          # orchestrator ExportService.export(shop_id, period) -> bytes|path
  zip_transport/   # manifest + zip encode (stdlib zipfile)
scripts/ai_package_v1_export.py  # CLI/Job entry, READ_ONLY_NO_MUTATION
tests/unit/ai_package_v1/        # contract tests (first slice)
tests/integration/ai_package_v1/ # optional CH/PG fixtures
```

### Dataset cards (v1)

Each dataset JSON card in manifest MUST include: `dataset_id`, `primary_source`,
`grain`, `period`, `collection_outcome`, `coverage`, `reason_codes[]`,
`freshness`, `provenance`, optional `row_file`.

| dataset_id | Primary source | Grain | v1 rows |
|---|---|---|---|
| `campaign_full_stat` | `default_db.full_adv_wb_stat` | adv_id + date | yes |
| `complex_adv_funnel` | `default_db.wb_common_stat` | nmid + date (main nmid only) | yes |
| `campaign_settings_snapshot` | PostgreSQL inventory (`AdvSetting`+`WBCabinet` join) | adv_id (+ relation metadata) | conditional / PARTIAL; not detailed settings v1 |
| `shop_product_orders_sales` | `SOURCE_NOT_ASSIGNED` | n/a | metadata only |

### Pair Auto/Search

Export MUST list both `auto_adv_id` and `auction_adv_id` (when present) in scope
metadata and emit separate stat rows. Logical pair link MAY appear in manifest
metadata (campaign_id_auto, campaign_id_search) without new PG table (per strategy
decision).

### Determinism

Stable sort keys: `(dataset_id, campaign_id, date, nmid)`; UTF-8 JSON with
sorted keys; manifest file order fixed; `generated_at` either fixed in tests or
excluded from hash with documented `determinism_clock` test hook.

### Product Acceptance (planning)

```text
PRODUCT_ACCEPTANCE_REQUIRED: true
PRODUCT_ACCEPTANCE_STATUS: BLOCKED (pre-apply — SIDE_EFFECT_PROOF pending implementation/tests; scenario plan material does not waive PA)
NORMATIVE_MODALITY_PRESERVED: yes
DESIGN_STATUS: READY
TECHNICAL_DESIGN_UNRESOLVED: none (detailed settings snapshot deferred to future change; inventory seam in tasks §1.2)
```

Scenario coverage: authoritative plan evidence is
`scenario-coverage/plan.md` + `scenario-coverage/plan.receipt.json` (official
`mode=plan` only). Gates MUST verify receipt `INPUTS` content hashes against
current `design.md`, `owner-contract.md`, and delta specs — do **not** embed
`PLAN_EVIDENCE_ID` or receipt content hashes in those input files. After
planning-input edits, refresh via `/opsx-spec-scenario-coverage … mode=plan`.
**Plan ready** is distinct from **audit/certify** (`mode=audit`, post-apply).
Do not manually edit receipt or plan to refresh hashes.

## Non-goals

Collectors, DDL, TG/GUI, AI JSON response, preview/apply, `inc-ro-08`, sibling
`shop-wide-campaign-data-collection`.

## Open Questions (harmless)

- Exact CLI flag names for Job wrapper — naming only at apply.
- Whether v1 slice ships PG snapshot card as `UNKNOWN` until discovery completes
  (recommended default in tasks).
