---
cursor:
  subagentId: "bc-83f679b5-0e09-5aef-b1da-1777b57ba72f"
---

# Re-review — 1b636542

Parent `a776b2b35ad65a0200f43aaeee2bcd78309cb481`. History `23c0671f3 → f3b1e5289 → 1a9c3320b → a776b2b35 → 1b636542a`. Merge-base with `144364928` is `23c0671f3`. That commit is not an ancestor. `HISTORY_OK: YES`.

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
MISSING_ZERO_NULL: PASS
JOINABILITY: PASS
ZIP_DETERMINISM_CONTRACT: PAYLOAD_DETERMINISTIC
DETERMINISM: PASS
AI_READABILITY: PASS
SCOPE_OK: YES
HISTORY_OK: YES
MERGE_REVIEW: PASS
BLOCKERS: NONE
```

## The two fixes

`campaign_settings_current` value semantics now name `CampaignSettingsSnapshotV1` JSON: a missing record, a numeric 0 inside a present record, and JSON null as absent or unknown. They do not describe a CSV day-row (`package_summary.py` `_value_semantics_for_family`).

`build_shop_product_orders_sales_card` sets `row_count=None` and still uses `SOURCE_NOT_ASSIGNED` / `UNKNOWN` (`domain/cards.py`). `to_manifest_dict` omits `row_count` when it is null, and also drops `row_count` 0 when derived `family_status` is GAP (`dataset_card.py`). Summary `shop_common_sales` stays GAP with reasons `SOURCE_NOT_ASSIGNED` and `UNKNOWN`. The integration test now requires `shop_orders.row_count is None`. `tests/unit/ai_package_v1/test_campaign_settings_contract.py` is not in the diff.

## Locks still held

This commit does not touch keyword paths, gap-catalog append, `family_status` reads, daily `leg_role` primary key, `campaign_id_equals_physical_adv_id`, settings PARTIAL / history GAP / change-events GAP, `PAYLOAD_HASH_ONLY`, or `encode_package` (`ZipFile.writestr`, no timestamp normalization). No new collectors and no second exporter. The extra test edit is the sales `row_count` assertion in `test_export_settings_integration.py`.

## Residual, not a blocker

`keyword_performance` summary `row_count` is still the first keyword card only. `keyword_current_state` and `keyword_changes` field-matrix rows still do not mark `leg_role` as a primary key. Daily primary key, matrix flag, and card grain still agree.
