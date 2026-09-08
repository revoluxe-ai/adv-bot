# Production fix evidence CHILD-001

BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: CHILD-001
COMMAND: /opsx-fix-bug GO
WORKER_ID: WEX_FIXBUG_CHILD_001_GO
CREATED_AT: 2026-09-08T02:45:00Z

## Change summary

Runtime CPO/plan overlay SoT wired through `PlanFactProvider.get_effective_plan_data(..., complex_adv=...)` for keyword GOOD/BAD above-target gate, telegram cost-activity menu, and `is_auto_campaign_active` wrapper.

## Files changed

- app/modules/wb_adv_updater/calculated_keywords_manager/calculated_keywords_manager.py
- app/shared/domains/wb/utils/auto_campaign_cost_activity.py
- app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py

## Invariant restored

Consumers (keyword classification above-target gate, telegram cost-activity metrics, `is_auto_campaign_active`) no longer resolve plan thresholds from base `AdvSetting` columns or call cost-activity without `ComplexAdv` / attached runtime `promo_fraction` when overlay fraction lives on `ComplexAdv`.

## Optional pytest check (fix-bug hop, not GREEN writer)

```text
poetry run pytest tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py -vv
```

Exit code: 0 (PASSED — 3/3)

## Next

GREEN confirmation owned by `/opsx-test verify`:

```text
/opsx-test case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z finding=CHILD-001 verify
```

STATUS: PRODUCTION_PATCH_APPLIED
GREEN_EVIDENCE_PATH: (pending /opsx-test verify)
