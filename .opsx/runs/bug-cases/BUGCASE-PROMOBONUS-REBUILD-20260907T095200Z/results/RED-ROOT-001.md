# RED evidence: ROOT-001

```text
TEST_ID: tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: ROOT-001
COMMAND: poetry run pytest tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive -vv --tb=short
EXPECTED_FAILURE: rec-bid plan_context keeps unscaled AdvSetting target/max pay (100/200) because AutoShelfBidControlViewProvider.build_view calls PlanFactProvider.get_effective_promo_plan(adv) without fraction=/complex_adv=, so overlay stays f=0 despite raise_plan_on_promobonuses and live promo_fraction=0.2 (expected overlay 125/250)
ACTUAL_FAILURE: assert 100.0 == 125.0 (PlanContext.target_order_cost=100.0, max_order_cost=200.0) at tests/unit/test_auto_shelf_bid_control_view_provider.py:1655
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:c13aad58d5ff5a90428f7c7fe18a9516ab38921213bc395a8f3cd9e64ac58d40 (app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py, unchanged); sha256:3215cfe3f199dc83cdb21f11bc43b970e3b12fcfde2321ec1a438e7a22e002c5 (app/modules/plan_fact/provider.py, unchanged)
TEST_CONTENT_SHA256: 7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive`
- failure: `assert 100.0 == 125.0` on `plan_context.target_order_cost` (unscaled 100 vs overlay 125 at f=0.2 / M=1.25)
- `get_effective_promo_plan` was not mocked away (spy call-through); overlay stayed f=0 because call site omits `fraction=` / `complex_adv=`
- production not modified during RED authorship

## Behavior protected

Telegram rec-bid `build_view` must feed overlay target/max pay into `plan_context` when `raise_plan_on_promobonuses` is on and live `promo_fraction > 0`. Removing overlay kwargs (f=0) must fail this test.
