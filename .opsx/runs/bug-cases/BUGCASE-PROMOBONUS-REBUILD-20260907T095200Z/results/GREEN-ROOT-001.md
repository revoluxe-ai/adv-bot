# GREEN evidence: ROOT-001

```text
TEST_ID: tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: ROOT-001
COMMAND: poetry run pytest tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/test_auto_shelf_bid_control_view_provider.py -vv --tb=short
PRODUCTION_HASH_BEFORE: sha256:c13aad58d5ff5a90428f7c7fe18a9516ab38921213bc395a8f3cd9e64ac58d40 (app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py); sha256:3215cfe3f199dc83cdb21f11bc43b970e3b12fcfde2321ec1a438e7a22e002c5 (app/modules/plan_fact/provider.py)
PRODUCTION_HASH_AFTER: sha256:cddf5e8bf9dbdc3ca01beb5712871d185f4d37c616775a6a6cc0f5b984c0e315 (app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py, changed vs RED); sha256:3215cfe3f199dc83cdb21f11bc43b970e3b12fcfde2321ec1a438e7a22e002c5 (app/modules/plan_fact/provider.py, unchanged)
TEST_CONTENT_SHA256: 7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: Telegram rec-bid plan_context uses overlay target/max pay when live promo_fraction > 0 (expected 125/250 at f=0.2, not raw AdvSetting 100/200)
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- Adjacent cheap pair: frozen node + `test_build_view_rec_bid_recommendation_fail_soft` — 2 passed in 0.34s (exit 0).
- Adjacent view_provider unit file: collected 34 items; 34 passed, 1 warning in 2.26s (exit 0). Frozen node included and PASSED.
- `TEST_CONTENT_SHA256` of `tests/unit/test_auto_shelf_bid_control_view_provider.py` equals RED frozen hash `7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae` (no test edits).
- Production view_provider hash after ≠ RED before (`cddf5e8b…` vs `c13aad58…`).
- Tests not edited. Production not edited this hop.

## Invariant verified

Telegram rec-bid `plan_context` uses overlay target/max pay when live `promo_fraction > 0`.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/c633e1549e`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
