# RED evidence CHILD-001

TEST_ID: tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting
BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: CHILD-001
COMMAND: /opsx-fix-bug
CREATED_AT: 2026-09-08T02:30:00Z

## Expected failure

При ``promo_fraction=0.5`` на ``ComplexAdv`` (effective max CPO=200 при base max=100)
ключ с CPO≈150 на пороге МС должен остаться ``GOOD`` (``WHITE_LIST``), потому что
150 < 200. Текущий production читает ``adv_setting.max_price_for_order`` (base=100)
в ``__get_calculated_keywords`` и помечает ключ ``BAD`` (``ABOVE_TARGET_AT_MIN_BID``).

Дополнительные failing nodes (тот же файл):

- ``test_telegram_menu_cost_activity_path_must_match_overlay_when_fraction_on_complex_adv``
- ``test_is_auto_campaign_active_accepts_complex_adv_for_overlay_fraction``

## Actual failure

```text
AssertionError: assert <KeywordStatus.BAD: 'bad'> == <KeywordStatus.GOOD: 'good'>
```

Telegram-path node:

```text
AssertionError: assert 100.0 == 200.0  # menu_metrics.target_cost vs overlay_metrics.target_cost
```

Wrapper node:

```text
assert 'complex_adv' in inspect.signature(is_auto_campaign_active).parameters
```

## Pytest command

```text
poetry run pytest tests/unit/app/modules/promobonus_overlay/test_child_001_incomplete_overlay_wiring.py -vv
```

Exit code: 1 (FAILED — 3 failed)

FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:4357bcb4c3a558bc9dffac976e835067957db325bdbbc561706fbc8e55a4c729
PRODUCTION_PATH: app/modules/wb_adv_updater/calculated_keywords_manager/calculated_keywords_manager.py; app/shared/domains/wb/utils/auto_campaign_cost_activity.py; app/client_bot/user_interface/views/messages/main_adv_setting_menu/adv_setting_menu.py
TEST_CONTENT_SHA256: 30d915f3b29ed2a6090cdfc65a645f2cafd1bc2939c14fa3362601bbc6e4be06
STATUS: RED_CONFIRMED

## Invariant under test

Runtime CPO/plan overlay MUST be single SoT via ``PlanFactProvider.get_effective_plan_data``
/ promo overlay with ``ComplexAdv``. Consumers (keyword GOOD/BAD above-target gate,
telegram cost-activity, ``is_auto_campaign_active`` wrapper) MUST NOT use base
``AdvSetting`` plan columns or call cost-activity without ``ComplexAdv`` when
``promo_fraction`` lives only on ``ComplexAdv``.

## Next

Owner may append ``GO`` after RED gate, then:

```text
/opsx-fix-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z intake=INTAKE-002 finding=CHILD-001 claim_token=CLAIM/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/CHILD-001/2026-09-08T02:16:54Z GO
```
