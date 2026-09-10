# FIX-ROOT-001

## Status

Implemented Telegram rec-bid overlay: `build_view` now passes live `promo_fraction` into `PlanFactProvider.get_effective_promo_plan`.

## Changed paths

- `app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py`

## Rationale

Call site previously used `get_effective_promo_plan(adv)` without `fraction=` / `complex_adv=`. AdvSetting does not store live promo share; f lives in Redis overlay cache. `build_view` has no `ComplexAdv` with `promo_fraction` in rec-bid scope (the later `_ViewComplexAdv` is for decision snapshot and does not carry overlay).

Fix uses the existing overlay architecture (`fraction_from_cached_state` + `get_effective_promo_plan(..., fraction=)` as `overlay_for_adv`):

1. Read Redis via `RedisPromoStateManager.get(shop_id)` (same seam the frozen RED test patches).
2. Resolve `f` with `fraction_from_cached_state(cached, adv_id, search_adv_id)`.
3. Miss / invalid `shop_id` / Redis error → `Decimal("0")` (conservative M=1).
4. Rec-bid `plan_context` target/max pay come from overlay Plan (125/250 at f=0.2), not raw AdvSetting 100/200.

No second overlay architecture. Intake items 2-6 not started. Frozen test file not modified.

## Commands and results

- Frozen test SHA256: `7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae` (unchanged)
- `poetry run pytest tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_recommendation_fail_soft -vv --tb=short`
  - PASS: 2 passed.

ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug

MISSION_COMPLETE: no
FINDING_TERMINAL: no
