---
cursor:
  subagentId: "bc-83f679b5-0e09-5aef-b1da-1777b57ba72f"
---

# Independent review — Full AI Package contract repair

Reviewed code at `1a9c3320bdab5a1c0db7f74542b5f1aa4101b763` on `cursor/ai-package-full-export-contract-repair-6076` against baseline `23c0671f372f0435b13a3573ec8990b4303b3e4a`. Implementer notes and `FULL_AI_PACKAGE_ACCEPTANCE_REPORT.md` were not used as grades.

## Verdict

```text
PACKAGE_SUMMARY: FAIL
CANONICAL_FAMILY_STATUS: FAIL
CAMPAIGN_IDENTITY: PASS
KEYWORD_IDENTITY: PASS
SETTINGS_CURRENT: PARTIAL
SETTINGS_HISTORY: GAP
CHANGE_EVENTS: GAP
COMMON_SALES: GAP
CAMPAIGN_ADVERTISING: PARTIAL
MISSING_ZERO_NULL: FAIL
JOINABILITY: FAIL
ZIP_DETERMINISM_CONTRACT: PAYLOAD_DETERMINISTIC
DETERMINISM: PASS
AI_READABILITY: FAIL
SCOPE_OK: YES
MERGE_REVIEW: FAIL
BLOCKERS:
- PACKAGE_SUMMARY is not a complete family index and mislabels keyword reasons, keyword paths, and campaign/funnel available dates
- FamilyStatus is not on dataset cards; summary ignores gap catalog family_status
- GAP families publish row_count 0 while the global rule says 0 is an observed zero; current settings semantics describe CSV
- Keyword join documentation inside DATA_MAP disagrees with itself, and the summary pointer does not name real keyword files
```

## PACKAGE_SUMMARY — FAIL

`build_package_summary_document` (`app/modules/ai_package_v1/export/package_summary.py`) is a deterministic builder (canonical JSON, not a model). It emits schema versions, `shop_id`, `export_period`, `effective_coverage`, `campaign_identity`, `missing_zero_null`, and pointers to `DATA_MAP.json`, `PACKAGE_FAMILY_GAPS.json`, and `manifest.json`.

It does not inventory every family. The gap catalog (`app/modules/ai_package_v1/export/family_gaps.py`) also lists `shop_inventory_discovery`, `store_drr`, `product_prices_stocks`, and `finance_promo`. Those ids are absent from `families`. Sales is `shop_common_sales` in the summary and `shop_product_orders_sales_feed` in the gaps file.

`keyword_performance` is built with `card=None` (same file, the `_entry_from_card` call). That forces `dataset_ids=[]`, `row_count=None`, and `status_reason_codes=["CARD_MISSING"]` via `_reason_codes_from_card`, even though keyword cards are on the manifest. The pointer is `datasets/keyword_*.jsonl`. Real paths are `keyword_performance/keyword_daily.jsonl` and siblings (`app/modules/ai_package_v1/keyword_performance/export/dataset_cards.py`).

`first_available_date` / `last_available_date` for `campaign_advertising` and `complex_adv_funnel` are `period.start` / `period.end`, including when the fixture has zero rows.

`effective_coverage` is worst-wins over every family, including permanent GAP catalog entries, so a v1 package is GAP even when exported slices are only partial. That rule is not in the JSON.

## CANONICAL_FAMILY_STATUS — FAIL

`FamilyStatus` in `app/modules/ai_package_v1/domain/enums.py` is `COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED`. Its docstring says it does not replace `CollectionOutcome` / `Coverage` on dataset cards. Manifest cards still have no `family_status` field. `derive_family_status_from_card` never returns `UNSUPPORTED`.

Gaps and summary both print `family_status`, but the summary does not read that field:

```text
history_status = family_status_for_gap_entry(str(history_gap.get("status", "GAP")))
change_status = family_status_for_gap_entry(str(change_gap.get("status", "GAP")))
```

The catalog key is `family_status`. `.get("status", "GAP")` always takes the default. Current catalog values are GAP, so tests pass. Unknown tokens coerce to GAP in `family_status_for_gap_entry` (`tests/unit/ai_package_v1/test_family_status.py`). The validator rejects unknown tokens in the files, then only cross-checks campaign advertising, the keyword aggregate, and settings history (`package_validator.py`). It does not check change events, funnel, or current settings against cards.

## CAMPAIGN_IDENTITY — PASS

CSV columns are still `shop_id, campaign_id, date, views, clicks` (`payload_encode.py`). `CampaignStatRow.campaign_id` and `assert_no_synthetic_merge` are unchanged. Summary and DATA_MAP now state `campaign_id_equals_physical_adv_id: true`, distinguish PG `adv_setting_id` from physical WB adv id, and say Auto and Search must not be summed (`package_summary.py` `_campaign_identity_block`, `data_map_builder.py` `campaign_identity`).

## KEYWORD_IDENTITY — PASS

Daily identity in code includes `leg_role` (`keyword_performance/windows/engine.py` `_identity_key`). `KeywordDailyRowV1.leg_role` is required. This change adds `leg_role` to `DATA_MAP.datasets.keyword_daily.primary_key` and to summary `primary_join_keys`. Domain grain was not rewritten for export. The field-matrix `pk` flag still omits `leg_role`; that contradiction is under JOINABILITY, not a missing key.

## Settings / sales / advertising

| Slice | Grade | Cause in code |
|---|---|---|
| SETTINGS_CURRENT | PARTIAL | `slice_kind=CURRENT`. Card from `build_detailed_campaign_settings_card`; PG path carries `PARTIAL_PG_WB_SYNC`. Not labeled HISTORY. |
| SETTINGS_HISTORY | GAP | Separate family, `slice_kind=HISTORY`, gap notes say CH history is outside v1 ZIP. No new collector. Reason code on the entry is only `UNKNOWN`. |
| CHANGE_EVENTS | GAP | New catalog family only. Notes say no read-only collector. No persistence added. |
| COMMON_SALES | GAP | `build_shop_product_orders_sales_card` is `SOURCE_NOT_ASSIGNED` + `UNKNOWN` (`domain/cards.py`). Summary hardcodes GAP. Not filled from funnel (`assert_funnel_orders_do_not_populate_shop_product_orders`). Contract gap, not a fixture relabeled as a product bug. |
| CAMPAIGN_ADVERTISING | PARTIAL | Acceptance fixture uses `_NoOpReader` (zero CH rows). `build_campaign_full_stat_card` then sets collection `PARTIAL`, coverage `UNKNOWN` (`coverage_for_empty_campaign_stat` returns UNKNOWN for sole `NO_DATA`), reason `NO_DATA`. Derivation maps collection PARTIAL to FamilyStatus PARTIAL. Rows are not invented. |

## MISSING_ZERO_NULL — FAIL

Global invariant says numeric 0 is an observed zero (`_MISSING_ZERO_NULL_GLOBAL`). History and change-event entries set `row_count=0`. The sales card also has `row_count=0`, which the summary copies. That publishes a zero count for families that were not collected.

`campaign_settings_current` falls through to the generic semantics: "no CSV row" / "numeric 0 in CSV" / "null not used in CSV". The payload is `datasets/campaign_settings_snapshot.json`. The unit test only checks that the `missing` string differs from the `zero` string.

Keyword JSONL text in DATA_MAP (`missing_zero_null`) matches the existing null-vs-zero field registry. That part is fine. The index counts are not.

## JOINABILITY — FAIL

Campaign stat join keys `shop_id, campaign_id, date` match the CSV, and the identity block explains `campaign_id` = physical adv id = keyword `adv_id`. Settings keys name `adv_setting_id`, `auto_leg`, `search_leg`, which exist on `CampaignSettingsSnapshotRecordV1` (`adv_setting_id` nested under `inventory`).

An external reader still cannot join keyword rows from PACKAGE_SUMMARY + DATA_MAP alone:

- Summary pointer `datasets/keyword_*.jsonl` does not match `keyword_performance/*.jsonl`.
- DATA_MAP `primary_key` includes `leg_role`. `export_field_matrix` marks `primary_key: true` on `adv_id`, `nmid`, `norm_query`, `date` only (`export_field_registry.py`). Manifest card grain is `adv_id × nmid × norm_query × date` (`build_keyword_daily_card`).
- Window identity also includes `adv_setting_id` (`_identity_key`). That column is not in the documented primary key.
- Campaign/funnel "available" dates are the request window, so a date join overstates coverage when `row_count` is 0.

## ZIP_DETERMINISM_CONTRACT — PAYLOAD_DETERMINISTIC

Pre-existing contract, `openspec/specs/ai-package-v1-exporter/spec.md` ("Versioned manifest with sha256"): identical inputs must repeat per-file `sha256` and the manifest hash. Contract tests (`openspec/specs/ai-package-v1-contract-tests/spec.md`) require manifest sha256 on a fixed clock, and keyword manifest + DATA_MAP sha256 at the same `generated_at`. Neither text requires byte-identical ZIP archives.

`encode_package` still uses `ZipFile.writestr` (`zip_transport/encode.py`) and does not normalize `ZipInfo` timestamps. This change does not add that normalization. It sets `zip_determinism_contract: PAYLOAD_HASH_ONLY` on the summary and drops ZIP-byte equality from `test_package_zip_payload_hash_deterministic`, `test_full_ai_package_acceptance_twice`, and `test_export_zip_deterministic_settings_hash`.

`design.md` states payload-hash as the accepted contract and defers byte-identical ZIP in prose. There is no architecture decision file and no tracked follow-up defect. That is a process gap, not a silent expansion of byte-ZIP.

## DETERMINISM — PASS

Same `generated_at` reruns compare `payload_sha256_map` and require equality. Domain CSV hashes stay equal when `generated_at` changes (`test_package_summary.py`). The trailing `zip_hash_a != zip_hash_b or hashes_a != hashes_b` assert is weak, but the stable-file asserts are real. Acceptance still writes `determinism="PASS"` into the report object before those asserts.

## AI_READABILITY — FAIL

Acceptance marks PASS when `campaign_identity` and `missing_zero_null` are present and DATA_MAP `primary_key` contains `leg_role` (`test_full_package_acceptance.py`). An external consumer of PACKAGE_SUMMARY + DATA_MAP still needs source or `manifest.json` for keyword file paths, keyword dataset ids, and real row counts. `CARD_MISSING` is a builder artifact. Available dates for campaign and funnel are the requested period. Four gap families are only in `PACKAGE_FAMILY_GAPS.json`. Current-settings zero/missing text describes CSV.

## SCOPE_OK — YES

Diff stays in summary, family status, gap field rename `status` → `family_status`, DATA_MAP docs, validator, and unit tests. `PackageZipAssembler` still calls `ExportService` then `attach_family_gaps` then `attach_package_summary` then `encode_package`. No ChangeSet, settings apply, production write, settings-history collector, change-event store, or second exporter. Archived `openspec/changes/archive/2026-10-05-ai-package-full-export` is not the active change. Active change is `openspec/changes/ai-package-full-export-contract-repair`.

## MERGE_REVIEW — FAIL

Do not merge until the summary index, family-status wiring, missing-versus-zero counts, and keyword pointers/keys are fixed and tested against the ZIP contents rather than key presence.
