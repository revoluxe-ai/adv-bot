# Bounded hunt proof — PROMO-OVERLAY-REC-BID

```text
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/266277452c
FINDING_ID: ROOT-001
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID
HUNT_RESULT: CLEAR
CANDIDATE_COUNT: 0
```

## Result

HUNT_RESULT: CLEAR. No remaining same-invariant production call of
`PlanFactProvider.get_effective_promo_plan` on rec-bid / Telegram
`plan_context` display without `fraction=` or `complex_adv=`.
ROOT-001 was not re-opened (view_provider already passes
`fraction=live_fraction`).

## Hunt bound

Find only same-invariant call sites that compute rec-bid / Telegram plan
display via `get_effective_promo_plan` without passing live overlay
fraction or `complex_adv`. Do not hunt intake items 2-6 (ledger
accounting leftover journal). Do not fix, test, classify, or close.

## Files inspected

- `app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py`
- `app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_decision_snapshot_builder.py`
- `app/shared/domains/wb/utils/promo_overlay.py`
- `app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/rec_bid_plan_context.py`
- `app/client_bot/user_interface/views/messages/auto_shelf_bid_control_render.py`
- `app/modules/plan_fact/provider.py` (definition + `get_effective_plan_data` wrapper)
- Repo-wide `get_effective_promo_plan(` usages (production + the frozen-test spy)

## `get_effective_promo_plan` call sites

| Site | kwargs | Classification |
|------|--------|----------------|
| `auto_shelf_bid_control_view_provider.py` ~914 | `fraction=live_fraction` after `_resolve_live_promo_fraction(adv)` | Telegram rec-bid `plan_context` (ROOT-001 fix). Not re-opened. |
| `auto_shelf_bid_control_decision_snapshot_builder.py` ~110 | `complex_adv=complex_adv` | Sibling rec-bid for PLAN_DISTANCE snapshot. Passes `complex_adv=`. |
| `promo_overlay.py` `overlay_for_adv` ~41 | required `fraction=fraction` | Helper. Shop-data attach path, not Telegram rec-bid display. |
| `plan_fact/provider.py` `get_effective_plan_data` ~134 | forwards `fraction=` and `complex_adv=` | Wrapper, not a display site. |
| `plan_fact/provider.py` ~144 | definition | Not a call site. |
| `tests/unit/test_auto_shelf_bid_control_view_provider.py` | spy + expected overlay with `fraction=live_fraction` | Test-only. Not a production violation. |

No other production `get_effective_promo_plan(` call sites exist in the repo.

## Closely related rec-bid / Telegram display

- `rec_bid_plan_context.py` `build_rec_bid_plan_context` does not call
  `get_effective_promo_plan`. Both production callers pass overlay
  target/max already resolved by the table above.
- Telegram renderer `auto_shelf_bid_control_render.py`
  `_render_rec_bid_recommendation_block` formats
  `view.rec_bid_recommendation`; it does not recompute plan overlay.
- `build_view` may later replace `rec_bid_recommendation` from
  `decision_snapshot` (~1176). That snapshot path is the sibling that
  already passes `complex_adv=` (see table). Not emitted as a candidate
  under this hunt bound (missing kwargs).

## Classified out of hunt bound (not candidates)

`get_effective_plan_data` callers are campaign/control/update paths, not
Telegram rec-bid `plan_context` display. All pass `complex_adv=` (or
`fraction=`). Not hunted as intake 2-6 / ledger:

- `auto_adv_active_control_service.py` ~1087 — `complex_adv=adv`
- `auto_updater_v3/data_update_manager/manager.py` ~117 — `complex_adv=complex_adv`
- `wb_shop_data_manager.py` ~335 — `complex_adv=complex_adv` (also `overlay_for_adv(..., fraction=fraction)` ~315)
- `update_cluster_bids_manager.py` ~992 — `complex_adv=adv`
- `adv_strategy_selector.py` ~113 — `complex_adv=complex_adv`
- `auto_campaign_cost_activity.py` ~102 — `complex_adv=` and `fraction=`

## Why CLEAR

Every production rec-bid / Telegram `plan_context` path that calls
`get_effective_promo_plan` already passes `fraction=` or `complex_adv=`.
The ROOT-001 site in `build_view` is the live-fraction path confirmed by
GREEN and is not re-opened. No `findings/HUNT-*.md` was written.

## HUNT_EFFECTIVENESS

HIGH_WITHIN_DECLARED_SCOPE: repo-wide `get_effective_promo_plan(`
enumeration completed; rec-bid/Telegram sites and sibling snapshot
inspected; unrelated ledger/accounting APIs classified out without
being treated as this invariant.

## HUNT_FALSE_NEGATIVE_RISK

BOUNDED_KWARGS_ONLY: hunt matches missing `fraction=` / `complex_adv=`
on rec-bid / Telegram display. Distant writers that never call this API
were not in scope. Telegram `build_view` may overwrite rec-bid with
snapshot rec-bid whose synthetic `ComplexAdv`-like object does not set
`promo_fraction`; that was not emitted because the snapshot call site
does pass `complex_adv=` and was declared sibling-compliant.
