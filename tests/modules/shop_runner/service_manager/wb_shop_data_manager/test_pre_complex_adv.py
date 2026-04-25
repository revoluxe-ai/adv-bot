from unittest.mock import MagicMock

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)


@pytest.mark.unit
def test_pre_complex_adv_resolved_target_plan_reached() -> None:
    pre_adv = PreComplexAdv(
        auto_adv=MagicMock(),
        plan_data=PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=800),
        plan_fact_summary=PlanFactSummary(
            adv_id=1,
            fact_predict_orders=120.0,
            fact_pay_for_order=450.0,
        ),
    )

    assert pre_adv.resolved_target_pay_for_order == 500.0
    assert pre_adv.target_pay_for_order == 500.0


@pytest.mark.unit
def test_pre_complex_adv_resolved_target_plan_not_reached() -> None:
    pre_adv = PreComplexAdv(
        auto_adv=MagicMock(),
        plan_data=PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=800),
        plan_fact_summary=PlanFactSummary(
            adv_id=1,
            fact_predict_orders=30.0,
            fact_pay_for_order=900.0,
        ),
    )

    assert pre_adv.resolved_target_pay_for_order == 800.0


@pytest.mark.unit
def test_pre_complex_adv_resolved_target_none_when_missing_data() -> None:
    pre_adv = PreComplexAdv(
        auto_adv=MagicMock(),
        plan_data=None,
        plan_fact_summary=None,
    )

    assert pre_adv.resolved_target_pay_for_order is None
