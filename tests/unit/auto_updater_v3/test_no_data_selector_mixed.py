"""Unit: NO_DATA — ключи без V2 CPO → MIN_CPA; с V2 CPO → M1/M2/M3."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import (
    FactMethods,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_actions,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _kw as _calculated_kw_fixture,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _sample_profile,
)


@pytest.mark.unit
def test_no_data_campaign_skips_m3_when_campaign_pay_for_order_is_none() -> None:
    """NO_DATA: M1/M2 по ключам с V2 CPO; M3 не вызывается (нет campaign fact CPO)."""
    off_no_cpo = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    min_with_cpo = _calculated_kw_fixture(
        ks_id=2,
        text="b",
        mode=KeywordStrategyMode.MIN_CPA,
        conv=0.08,
        cpm_set_bid=200,
    )
    profile = _sample_profile()
    contexts = [
        KeywordV3Context(keyword=off_no_cpo, position_profile=profile),
        KeywordV3Context(keyword=min_with_cpo, position_profile=profile),
    ]
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=None,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.selector.plan_mass_cheap_promotion",
            return_value=[],
        ) as m1_mock,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.selector.plan_state_rebalance",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.selector.plan_headroom_plus_one",
        ) as m3_mock,
    ):
        actions = select_v3_actions(
            state=SalesStates.NO_DATA,
            contexts=contexts,
            shelf_promotion_active=False,
            plan=plan,
            fact=fact,
        )

    m1_mock.assert_called_once()
    m3_mock.assert_not_called()
    assert any(a.reason == "no_data_min_bid" for a in actions)


@pytest.mark.unit
def test_no_data_campaign_merges_min_up_and_rollout_for_keys_with_cpo() -> None:
    """Кампания NO_DATA: OFF без CPO → UP; ключ с CPO участвует в M1."""
    off_no_cpo = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    min_with_cpo = _calculated_kw_fixture(
        ks_id=2,
        text="b",
        mode=KeywordStrategyMode.MIN_CPA,
        conv=0.08,
        cpm_set_bid=200,
    )
    profile = _sample_profile()
    contexts = [
        KeywordV3Context(keyword=off_no_cpo, position_profile=profile),
        KeywordV3Context(keyword=min_with_cpo, position_profile=profile),
    ]
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=None,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.selector.plan_mass_cheap_promotion",
        return_value=[],
    ) as m1_mock:
        actions = select_v3_actions(
            state=SalesStates.NO_DATA,
            contexts=contexts,
            shelf_promotion_active=False,
            plan=plan,
            fact=fact,
        )

    assert any(
        a.action == V3ActionType.UP
        and a.keyword_setting_id == 1
        and a.reason == "no_data_min_bid"
        for a in actions
    )
    m1_mock.assert_called_once()
    prepared_arg = m1_mock.call_args[0][0]
    assert len(prepared_arg) == 1
    assert prepared_arg[0][0].keyword.text == "b"
