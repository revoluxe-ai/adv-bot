import pytest


from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import \
    detect_campaign_state, SalesStates

pytestmark = pytest.mark.integration


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

@pytest.mark.asyncio
def test_detect_campaign_state(plan, fact, expected_state):
    state = detect_campaign_state(plan, fact)
    assert state == expected_state
