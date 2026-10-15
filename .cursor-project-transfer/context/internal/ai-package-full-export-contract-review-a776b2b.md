---
cursor:
  subagentId: "bc-83f679b5-0e09-5aef-b1da-1777b57ba72f"
---

# Re-review — a776b2b

Parent `1a9c3320bdab5a1c0db7f74542b5f1aa4101b763`. History `23c0671f3 → f3b1e5289 → 1a9c3320b → a776b2b35`. Merge-base with `origin/stage` and with `144364928` is `23c0671f3`. `144364928` is not an ancestor. `HISTORY_OK: YES`.

## Verdict

```text
PACKAGE_SUMMARY: PASS
CANONICAL_FAMILY_STATUS: PASS
CAMPAIGN_IDENTITY: PASS
KEYWORD_IDENTITY: PASS
SETTINGS_CURRENT: PARTIAL
SETTINGS_HISTORY: GAP
CHANGE_EVENTS: GAP
COMMON_SALES: GAP
CAMPAIGN_ADVERTISING: PARTIAL
MISSING_ZERO_NULL: FAIL
JOINABILITY: PASS
ZIP_DETERMINISM_CONTRACT: PAYLOAD_DETERMINISTIC
DETERMINISM: PASS
AI_READABILITY: PARTIAL
SCOPE_OK: YES
HISTORY_OK: YES
MERGE_REVIEW: FAIL
BLOCKERS:
- campaign_settings_current value_semantics still describes a CSV day-row, not the JSON CURRENT snapshot
- manifest sales card still publishes row_count 0 next to derived family_status GAP
```

## What the previous blockers did fix

`build_package_summary_document` appends every gap-catalog family (`package_summary.py` `_gap_catalog_entry` reads `family_status`). `keyword_performance` lists sorted keyword `dataset_ids` and `row_file` paths under `keyword_performance/`, plus `DATA_MAP.json` and `coverage.json`. `CARD_MISSING` is gone. Campaign and funnel first/last dates come from CSV column 3 via `_csv_date_bounds`; header-only files yield null, not `export_period`.

Manifest cards emit `family_status` from `derive_family_status_from_card` (`dataset_card.py` `to_manifest_dict`). Summary GAP rows omit `row_count` (`_serialize_family_entry`). Daily `primary_key`, `export_field_matrix` `primary_key: true` on `leg_role`, and `build_keyword_daily_card` grain all include `leg_role`.

## MISSING_ZERO_NULL — FAIL

`_value_semantics_for_family` still falls through for `campaign_settings_current` to "no CSV row for shop×entity×day" / "numeric 0 in CSV" / "null not used in CSV" (`package_summary.py` lines 149–153). The payload is `datasets/campaign_settings_snapshot.json`. `family_notes` correctly says CampaignSettingsSnapshotV1 CURRENT settings and not history. The semantics block contradicts that note. The unit test only checks that the two strings differ and that `family_notes` starts with `CampaignSettingsSnapshotV1`.

`build_shop_product_orders_sales_card` still sets `row_count=0` (`domain/cards.py`). `to_manifest_dict` now also writes `family_status` GAP (SOURCE_NOT_ASSIGNED) and still writes `row_count: 0`. Summary omits the count for the `shop_common_sales` family. The dataset card in the same ZIP does not.

## Status grades that stayed

`COMMON_SALES` stays GAP with `SOURCE_NOT_ASSIGNED` + `UNKNOWN`. It is not filled from funnel. `CAMPAIGN_ADVERTISING` stays PARTIAL from the empty `_NoOpReader` path (`NO_DATA`, coverage UNKNOWN, collection PARTIAL). `campaign_id_equals_physical_adv_id` is still true. Current settings stay PARTIAL (`slice_kind=CURRENT`). History and change events stay GAP catalog entries (`slice_kind` is now `GAP_CATALOG`; `family_id` and gap notes still separate them). No new collectors. Assembler still wraps ExportService. `encode_package` still uses `ZipFile.writestr` with no timestamp normalization. Follow-up is `openspec/changes/ai-package-full-export-contract-repair/decisions/zip-byte-identical-follow-up.md`. Payload-hash tests remain.

## Residuals (not the merge blockers)

`keyword_current_state` and `keyword_changes` field-matrix rows still do not set `pk=True` on `leg_role`. Keyword family `row_count` is the first keyword card only. Validator checks summary and gap tokens, not `family_status` on dataset cards. `effective_coverage` is still worst-wins across permanent GAPs.
