---
cursor:
  subagentId: "bc-4feed5c9-fa02-5492-84bb-c281e06b57c0"
---

# Review: separate-auto-search-cpo

HEAD `890799160` (feature vs merge-base `8d2383d6d`). Read-only. Verdict: **APPROVE**.

No CRITICAL, HIGH, or MEDIUM correctness bugs. Invariants hold on the reachable write paths.

## Checks

- Auto CPO is `compute_leg_cpo` of the Auto `adv_id` row only; Search CPO is the Search `adv_id` row only (`leg_cpo.py` `build_leg_cpo_snapshot`).
- Missing Search id, or a Search id with no CH rows, yields `None`, not `0` (`compute_leg_cpo(None)`). A present row is `spend / max(orders, 1)`, including `0` when spend is `0`.
- `ComplexAdv.attach_leg_cpo` raises `ValueError` on Auto or Search id mismatch (`complex_adv.py` ~626–641). No synthetic combined campaign id; snapshots are keyed by the real Auto `adv_id`.
- `fact_pay_for_order` stays the aggregate plan/fact field. V3 copies Search CPO into a new `FactData` (`model_copy`) and does not overwrite the aggregate.
- SQL `get_stats_by_adv_ids_last_days`: `argMax(*, version)` grouped by `adv_id, date`, then `SUM` grouped by `adv_id`. Same latest-version pattern as `get_stats_by_last_days` / `analysis_campaign_daily_by_adv_ids.sql`. Legs are not summed together.
- CH batch failure in `WBShopDataManager.attach_leg_cpo` leaves leg CPO unset (`None`). Destructive gates treat `None` as not-overspend (bidder cap, cluster cap `missing_fact_cpo`, A/B hold, Auto pause).
- Cluster bids (`update_cluster_bids_manager.py` ~992–1000) write `leg_snapshot.search_cpo` into `FactData.pay_for_order`. Bidder safety cap reads `dto.search_fact_cpo`.

## LOW

- Accepted: ruff UP037 quoted annotation, `app/modules/shop_runner/wb_stat_manager/leg_cpo.py:109`.
- `resolve_v3_fact_data` (`loaders.py` ~85–93) still returns `updater.get_fact_data` (aggregate mean CPO) when `dto` is missing or `max_last_period != 2`. Production `process_adv_v3` uses window `2`, and NORMAL / NO_DATA writes require `dto is not None`, which is only built for a linked Search leg and then uses `search_fact_cpo`. The else branch does not drive current Search writes.
- Campaign menu renders leg CPO with `.0f` (`adv_setting_menu.py` ~748–755). Keyword UI and automation keep the unrounded float. Same 2-calendar-day source; display rounding only.
- `test_get_stats_by_adv_ids_last_days_keeps_legs_separate` checks per-leg sums with one version per day. It does not repeat the multi-version `argMax` case already covered for `get_spend_by_last_days`.

## Not filed

`attach_leg_cpo` swallowing a CH exception is fail-closed (`None`), not a cross-leg fallback. `search_adv_id == 0` is already `None` via the AdvSetting property.
