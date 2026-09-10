# GREEN evidence CHILD-001

TEST_ID: tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting
BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: CHILD-001
COMMAND: /opsx-test verify
CREATED_AT: 2026-09-08T02:50:00Z

## Verification

Re-ran exact RED `TEST_ID` on production after `/opsx-fix-bug GO`.
`TEST_CONTENT_SHA256` matches RED (no assertion edits; no `NON_WEAKEN_DELTA`).

## Pytest command

```text
poetry run pytest tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting -vv
```

Exit code: 0 (PASSED)

## Hashes

PRODUCTION_HASH_BEFORE: sha256:4357bcb4c3a558bc9dffac976e835067957db325bdbbc561706fbc8e55a4c729
PRODUCTION_HASH_AFTER: sha256:f7ee81d503523cffe77088385662683faf884fba0ebe9df69a33614b70137872
PRODUCTION_PATH: app/modules/wb_adv_updater/calculated_keywords_manager/calculated_keywords_manager.py; app/shared/domains/wb/utils/auto_campaign_cost_activity.py; app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py
TEST_CONTENT_SHA256: 30d915f3b29ed2a6090cdfc65a645f2cafd1bc2939c14fa3362601bbc6e4be06
RED_EVIDENCE_PATH: results/RED-CHILD-001.md
FIX_EVIDENCE_PATH: results/FIX-CHILD-001.md

## Invariant confirmed

Runtime CPO/plan overlay SoT via `PlanFactProvider.get_effective_plan_data(..., complex_adv=...)`
drives keyword GOOD/BAD above-target gate (effective max=200 at promo_fraction=0.5, not base max=100).
Telegram cost-activity and `is_auto_campaign_active` accept/pass `ComplexAdv` for overlay fraction.

TARGETED_REGRESSIONS: tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting

STATUS: GREEN_CONFIRMED
