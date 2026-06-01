"""Unit: кампания NO_DATA — selector не двигает лестницу (оркестратор не вызывает)."""

from __future__ import annotations

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
def test_no_data_campaign_selector_waits() -> None:
    """Кампания NO_DATA: только DO_NOTHING (align V2 / orchestrator skip)."""
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
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.selector.select_v3_post_gate_actions",
    ) as post_gate_mock:
        actions = select_v3_actions(
            state=SalesStates.NO_DATA,
            contexts=contexts,
            shelf_promotion_active=False,
            plan=plan,
            fact=fact,
        )

    post_gate_mock.assert_not_called()
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DO_NOTHING
    assert actions[0].reason == "campaign_no_data_wait"
