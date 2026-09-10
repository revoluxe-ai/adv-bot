# Adjudication CHILD-001

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: CHILD-001
INTAKE_ID: INTAKE-002
COMMAND: /opsx-fix-bug
CREATED_AT: 2026-09-08T02:30:00Z
VERDICT: fix_now
GO_TOKEN: absent

## Summary

Incomplete overlay wiring: keyword classification, telegram cost-activity and
``is_auto_campaign_active`` wrapper still resolve plan thresholds from base
``AdvSetting`` or without ``ComplexAdv``, while watchdog/V3/shelf already use
``PlanFactProvider.get_effective_plan_data(..., complex_adv=adv)``.

## Reachability

- runtime_reachable: yes
- entrypoints: shop-runner → WBShopDataManager.get_complex_advs → CalculatedKeywordsManager.get_calculated_keywords; Telegram AdvSettingMenu.update_data; rec_system paths via is_auto_campaign_active
- write_boundary_reachable: yes (Redis calculated_keywords cache; telegram UI metrics)

## RED

STATUS: RED_CONFIRMED
RED_EVIDENCE_PATH: results/RED-CHILD-001.md
TEST_ID: tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting

## Fix plan (awaiting Owner GO)

1. ``calculated_keywords_manager.__get_calculated_keywords``: resolve plan scalars via ``PlanFactProvider.get_effective_plan_data(adv_setting, complex_adv=complex_adv)``.
2. ``is_auto_campaign_active``: add ``complex_adv`` param; forward to ``get_auto_campaign_cost_activity_metrics``.
3. ``calculated_keywords_manager`` rec_system branch: pass ``complex_adv`` to ``is_auto_campaign_active``.
4. ``adv_setting_menu``: resolve promo fraction / pass ``ComplexAdv`` or attach runtime ``promo_fraction`` before cost-activity call.

FORBIDDEN this episode: leftover/P0 mix, RaisePlanOnPromobonuses enablement, ROOT-001 mutation.
