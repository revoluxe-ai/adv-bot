---
cursor:
  subagentId: "bc-0a55fa12-200d-5dfa-b776-987fb4d86f8b"
---

# FULL_AI_PACKAGE_ACCEPTANCE_REPORT

Authority: `origin/stage` `23c0671f372f0435b13a3573ec8990b4303b3e4a` (2026-10-05 16:38:29 +0000, merge PR #448). Worktree HEAD `751e7bd2965a2d35941c5827a13cfab0ad6fc588` is the parent of that commit. `git diff HEAD origin/stage` is only `.cursor/environment.json`, `.cursor/rules/opsx-cloud-local-routing.mdc`, and `AGENTS.md`. `app/modules/ai_package_v1`, `scripts/ai_package_v1_export.py`, `tests/unit/ai_package_v1`, and `openspec/specs/ai-package-full-export` match stage. Product files were not edited.

Raw evidence: `internal/ai-package-full-export-acceptance-evidence.md`.

## Verdict block

```text
BASELINE_SHA:
23c0671f372f0435b13a3573ec8990b4303b3e4a

PACKAGE_GENERATED:
YES

PACKAGE_ENTRYPOINT:
scripts/ai_package_v1_export.py
(product CLI not executed: default ExportService needs PG/ClickHouse)
bounded proof: PYTHONPATH=. python3 /tmp/ai-package-acceptance/generate_bounded_package.py
via PackageZipAssembler.assemble_zip_with_scope + fixture ExportService
(same seam as tests/unit/ai_package_v1/test_package_zip_assembler.py)

MANIFEST:
PASS

DATA_MAP:
PASS

PACKAGE_SUMMARY:
FAIL

FAMILY_STATUS_EXPLICIT:
NO

CURRENT_SETTINGS:
PARTIAL

SETTINGS_HISTORY:
GAP

CHANGE_EVENTS:
GAP

KEYWORD_HISTORY:
PARTIAL

COMMON_SALES:
GAP

CAMPAIGN_ADVERTISING:
PARTIAL

JOINABILITY:
FAIL

MISSING_ZERO_SEMANTICS:
FAIL

COVERAGE_METADATA:
PASS

DETERMINISM:
FAIL

AI_READABILITY:
PARTIAL

BLOCKING_GAPS:
- PACKAGE_SUMMARY is absent from origin/stage (zero matches). Archived spec requires PACKAGE_FAMILY_GAPS.json, not a summary.
- Family status is not one enum. Manifest uses collection_outcome SUCCESS|PARTIAL|UNKNOWN and coverage FULL|PARTIAL|UNKNOWN. Gaps file uses GAP. coverage.json marks bid_decision_log UNSUPPORTED while manifest marks keyword_decisions PARTIAL/UNKNOWN/NO_DATA.
- Shop sales is split: manifest dataset shop_product_orders_sales is UNKNOWN with row_file null; gaps family_id shop_product_orders_sales_feed is GAP.
- Join identity campaign_full_stat.campaign_id == physical adv_id is not stated in package metadata. CSV header is campaign_id; manifest grain text says adv_id + date. Equivalence exists only in app/modules/ai_package_v1/sql/campaign_full_stat_by_adv_ids.sql and domain/campaign_stat.py.
- DATA_MAP keyword_daily grain includes shop_id, adv_setting_id, and leg_role; primary_key is only adv_id, nmid, norm_query, date. Manifest card grain drops shop_id and leg_role.
- Settings history and settings change events are not in the ZIP. PACKAGE_FAMILY_GAPS campaign_settings_history is GAP. The snapshot is one CampaignSettingsSnapshotV1 point in time, not a change log. keyword_changes are metric window deltas, not settings events.
- Deterministic ZIP fails across clock seconds. Run A ZIP SHA-256 25a05816b8a28320a87d4b40ed9a4ac12578bf5fac734adb70ec137372a59922. Run B ZIP SHA-256 1957b847cd753c19928645fc82aed69eb46956a88a474729786ad698ba43d710. Payload SHA-256 and CRCs match. encode_package uses ZipFile.writestr without a fixed ZipInfo.date_time. Unit test test_package_zip_deterministic_hash claims identical ZIP sha256 and passes only inside one wall-clock second.
- missing != zero is stated only on keyword coverage.json ("missing rows are null/absent; confirmed_zero is explicit only"). campaign_full_stat and complex_adv_funnel have no field-level null/zero/missing semantics.

NON_BLOCKING_GAPS:
- Operator CLI was not run. Bounded fixture package is the evidence. No production WB/PG/ClickHouse calls.
- Bounded campaign_full_stat and complex_adv_funnel are header-only, row_count 0, reason NO_DATA, because CH readers were no-ops. That is explicit emptiness, not a silent file omission.
- Keyword positions and decisions are empty files with NO_DATA. Daily row is factual (query_spend_status FACTUAL, spend_rub 50). raw_query is null with RAW_QUERY_UNAVAILABLE. No fabricated query spend in the package.
- source_calendar_timezone UNKNOWN is disclosed in DATA_MAP limitations. package_calculation_timezone is UTC.
- Explicit GAP catalog (not silent): shop_product_orders_sales_feed, campaign_settings_history, shop_inventory_discovery, store_drr, product_prices_stocks, finance_promo. Store DRR was not computed.
- pyright-strict skipped: VM Python 3.12.3, project requires >=3.11,<3.12.
- Unit gates passed: zip assembler, export settings integration, keyword export contract, datamap (36 tests in the evidence run). git diff --check clean.

RECOMMENDED_FOLLOW_UP:
Add root PACKAGE_SUMMARY.json as the only AI entry contract: one status enum per family (COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED), one id for shop sales, join glossary that campaign_id is physical adv_id, keyword primary key aligned with grain (include leg_role), settings slices labeled current vs history vs change-event, and missing!=zero scoped to every family. Do not reopen closed collectors. ZIP timestamp normalization is a separate defect (encode.py writestr); it is not this follow-up.

PRODUCT_CODE_CHANGED:
NO

PRODUCTION_WRITES:
NONE
```

## Paths on origin/stage

| Role | Path |
|------|------|
| ExportService | `app/modules/ai_package_v1/export/export_service.py` |
| PackageZipAssembler | `app/modules/ai_package_v1/export/package_zip_assembler.py` |
| Family gaps | `app/modules/ai_package_v1/export/family_gaps.py` → `PACKAGE_FAMILY_GAPS.json` |
| Manifest | `app/modules/ai_package_v1/domain/manifest.py` → `manifest.json` |
| DATA_MAP | `app/modules/ai_package_v1/keyword_performance/domain/data_map_builder.py` → `DATA_MAP.json` |
| Validator | `app/modules/ai_package_v1/validator/package_validator.py` (`validate_zip_package`) |
| Hash / ZIP | `app/modules/ai_package_v1/domain/manifest.py` `sha256_hex`; `app/modules/ai_package_v1/zip_transport/encode.py` `encode_package` |
| CLI | `scripts/ai_package_v1_export.py` |
| Spec | `openspec/specs/ai-package-full-export/spec.md` |
| PACKAGE_SUMMARY | not in tree |

## Independent consumer (bounded package only)

Packages: `/tmp/ai-package-acceptance/run-a/package.zip` and `run-b/package.zip`. Shop `1`, requested period `2026-01-01`..`2026-01-07`, `generated_at` `2026-10-05T12:00:00Z`. Validator accepted the ZIP.

1. Campaigns: one inventory record, `adv_setting_id` 101, name `Test Campaign`, physical auto `adv_id` 111, search `search_adv_id` 222.
2. SKUs: settings `nmids` `[111, 222]`. Keyword daily row `nmid` 500. Those sets are not the same, and the package does not explain the difference.
3. Periods: requested window 2026-01-01..2026-01-07. Keyword daily available 2026-01-01..2026-01-03 (`coverage_pct` 0.333). Position bounds 2026-01-01..2026-01-05 with zero position rows. WB reporting timezone UNKNOWN; calculation timezone UTC.
4. Current settings: one `CampaignSettingsSnapshotV1` at `snapshot_assembled_at` 2026-10-03T12:00:00Z. Coverage PARTIAL, `PARTIAL_PG_WB_SYNC`. Search-leg WB bid/status/payment/placement are null with authority UNKNOWN or UNSUPPORTED.
5. Settings history: GAP (`campaign_settings_history`). No change-event dataset. `keyword_changes` (180 lines) are keyword metric deltas (`3d_vs_prev_3d` and similar), not settings edits.
6. Keyword performance: one daily fact for `norm_query` `query`, `leg_role` AUTO, `adv_id` 111, `query_spend_status` FACTUAL, `spend_rub` 50, `cluster_avg_pos` 5, `raw_query` null. Windows 16 rows, current state 1 row. Positions and decisions are empty. Rebound is a documented `campaign_slot_role` (`REBOUND_HISTORICAL`); this fixture has no rebound row.
7. GAP/PARTIAL: six gaps-file families are GAP. Most materialized datasets are PARTIAL or UNKNOWN. `shop_inventory_discovery` GAP means campaign inventory completeness is not shop-wide proven.
8. Unsafe to interpret: shop orders/sales; settings history or “what changed”; WB calendar day; header-only stat/funnel as zeros; `campaign_id` as a different id from `adv_id`; keyword uniqueness if AUTO and SEARCH share a query (PK omits `leg_role`); empty position files as “position is zero”.

## Determinism exact result

| Check | Result |
|-------|--------|
| Payload file SHA-256 (manifest `files[].sha256`) | equal, 14 payloads |
| ZIP entry CRC and size | equal |
| Logical ordering | equal (sorted `logical_name`, manifest last) |
| Full ZIP SHA-256 | not equal (timestamps `(2026,10,5,17,1,8)` vs `(2026,10,5,17,1,10)`) |

Manifest hash contract is payload bytes (`sha256_hex`). The unit test additionally requires whole-ZIP equality. That second promise failed for two separate generations.
