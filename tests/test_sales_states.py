import pytest


from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import \
    detect_campaign_state, SalesStates

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('plan, fact, expected_state',
                         [(PlanData( #  Мало продаж - большой расход
                             orders=15,
                             target_pay_for_order=120,
                             max_pay_for_order=300,
                         ),
                            FactData(
                                 predict_orders=10.0,
                                 pay_for_order=500.0,
                                 original_orders=10,
                                 fact_method=FactMethods.DIRECT_SALES,
                            ),
                            SalesStates.OVERSPEND),
                              (PlanData( # Продаж больше чем надо и расход больше максимального
                                orders=10,
                                target_pay_for_order=120, # Если продаж достаточно, то смотрим на этот план-расход
                                max_pay_for_order=500,
                              ),
                            FactData(
                                 predict_orders=30,
                                 pay_for_order=350.0,
                                 original_orders=30,
                                 fact_method=FactMethods.DIRECT_SALES,
                            ),
                            SalesStates.STABLE),
                              (PlanData( # Продаж мало, расход меньше максимального
                                orders=30,
                                target_pay_for_order=120,
                                max_pay_for_order=300,
                              ),
                            FactData(
                                 predict_orders=10,
                                 pay_for_order=150.0,
                                 original_orders=10,
                                 fact_method=FactMethods.DIRECT_SALES,
                            ),
                            SalesStates.UNDERPERFORM),
                                (PlanData( # Всё в норме: продаж достаточно, расход меньше целевого
                                    orders=10,
                                    target_pay_for_order=200,
                                    max_pay_for_order=400,
                                ),
                            FactData(
                                 predict_orders=15,
                                 pay_for_order=150.0,
                                 original_orders=15,
                                 fact_method=FactMethods.DIRECT_SALES,
                            ),
                            SalesStates.OPTIMAL),
                         ])


def test_detect_campaign_state(plan, fact, expected_state):
    state = detect_campaign_state(plan, fact)
    assert state == expected_state


def test_detect_campaign_state_returns_no_data_when_fact_pay_for_order_is_none():
    """When fact has no pay_for_order data, state is NO_DATA (Н)."""
    plan = PlanData(orders=10, target_pay_for_order=200, max_pay_for_order=400)
    fact = FactData(
        predict_orders=15.0,
        pay_for_order=None,
        original_orders=15,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.NO_DATA


def test_detect_campaign_state_pay_equals_max_returns_optimal_when_under_orders():
    """pay == max: 90–100% зона стабилизации, не OVERSPEND и не UNDERPERFORM."""
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=300.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OPTIMAL


def test_detect_campaign_state_predict_orders_equals_plan_orders_stable_when_pay_above_target():
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=400)
    fact = FactData(
        predict_orders=10.0,
        pay_for_order=150.0,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.STABLE


def test_detect_campaign_state_predict_orders_equals_plan_orders_optimal_when_pay_equals_target():
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=400)
    fact = FactData(
        predict_orders=10.0,
        pay_for_order=100.0,
        original_orders=10,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OPTIMAL


def test_detect_campaign_state_overspend_priority_over_underperform():
    """pay_for_order > max triggers OVERSPEND even if predict_orders < plan.orders."""
    plan = PlanData(orders=30, target_pay_for_order=120, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=350.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OVERSPEND


def test_detect_campaign_state_returns_none_when_plan_fields_all_zero():
    plan = PlanData(orders=0, target_pay_for_order=0, max_pay_for_order=0)
    fact = FactData(
        predict_orders=1.0,
        pay_for_order=10.0,
        original_orders=1,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) is None


def test_detect_campaign_state_when_plan_orders_zero_treats_as_plan_met():
    """predict_orders >= plan.orders when plan.orders==0 — enters completed-plan branch."""
    plan = PlanData(orders=0, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=1.0,
        pay_for_order=50.0,
        original_orders=1,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OPTIMAL


def test_detect_campaign_state_optimal_when_below_plan_at_max_pay():
    """predict < plan и pay на потолке max — стабилизация (OPTIMAL), не NO_DATA."""
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=8.0,
        pay_for_order=300.0,
        original_orders=8,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OPTIMAL


def test_detect_campaign_state_underperform_when_below_plan_and_pay_below_90pct_max():
    """predict < plan и pay < 90% max — наращивание (UNDERPERFORM)."""
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=250.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.UNDERPERFORM


def test_detect_campaign_state_optimal_when_below_plan_in_90pct_band():
    """predict < plan, pay в [90%; max) — стабилизация."""
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=285.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.OPTIMAL
