
from typing import cast

import pytest
from unittest.mock import  patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system import (
    AdvControlSystem,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import ComplexAdv





@pytest.mark.parametrize("plan_data,fact_data,condition_func",
                    [
                        (PlanData(orders=15, target_pay_for_order=120,max_pay_for_order=300,), #  Мало продаж - большой расход
                    FactData(predict_orders=10.0, pay_for_order=500.0, original_orders=10,
                                 fact_method=FactMethods.DIRECT_SALES,),
                        lambda new_white_list_size, white_list_size, updated_adv_setting, complex_adv: \
                    any([new_white_list_size < white_list_size,
                     updated_adv_setting.max_place > complex_adv.target_place,
                     updated_adv_setting.exponent_predict_ctr > complex_adv.exponent_predict_ctr],
                                 )
                             and not any ([new_white_list_size > white_list_size,
                                  updated_adv_setting.max_place < complex_adv.target_place,
                                  updated_adv_setting.exponent_predict_ctr < complex_adv.exponent_predict_ctr]
                      )


                         ),
                     (PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж больше чем надо и расход больше максимального
                      FactData(predict_orders=30, pay_for_order=250.0, original_orders=10,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, complex_adv: \
                              any([new_white_list_size < white_list_size,
                                   updated_adv_setting.max_place > complex_adv.target_place,
                                   updated_adv_setting.exponent_predict_ctr > complex_adv.exponent_predict_ctr],
                                  )),
                     (PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж больше чем надо и расход больше максимального
                      FactData(predict_orders=30, pay_for_order=250.0, original_orders=10,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, complex_adv: \
                              any([new_white_list_size < white_list_size,
                                   updated_adv_setting.max_place > complex_adv.target_place,
                                   updated_adv_setting.exponent_predict_ctr > complex_adv.exponent_predict_ctr],
                                  )
                              and not any ([new_white_list_size > white_list_size,
                                  updated_adv_setting.max_place < complex_adv.target_place,
                                  updated_adv_setting.exponent_predict_ctr < complex_adv.exponent_predict_ctr]
                      )),
                     (

                    PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж мало, расход меньше максимального
                      FactData(predict_orders=1, pay_for_order=50, original_orders=1,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, complex_adv: \
                              any([new_white_list_size > white_list_size,
                                   updated_adv_setting.max_place < complex_adv.target_place,
                                   updated_adv_setting.exponent_predict_ctr < complex_adv.exponent_predict_ctr],
                                  ) and not any ([new_white_list_size < white_list_size,
                                  updated_adv_setting.max_place > complex_adv.target_place,
                                  updated_adv_setting.exponent_predict_ctr > complex_adv.exponent_predict_ctr])

                      ),])
@pytest.mark.asyncio(scope='function')
async def test_process_adv(postgres_session: AsyncSession,
                        complex_adv: ComplexAdv,
                           plan_data,
                           fact_data,
                           condition_func,
                           sm_generator,
                           di_containner_for_adv_auto_updater_v2
                           ):
    """Интеграционный тест для AdvControlSystem.process_adv с фейковыми данными."""

    control_system_v2 = AdvControlSystem(max_last_period=2)


    # 3️⃣ ComplexAdv мок (теперь с нормальной фабрикой)
    # 4️⃣ Мокаем план и факт
    with (
        patch(
            'app.modules.shop_runner.service_manager.'
            'old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.'
            'AdvSettingAutoUpdater.get_plan_data',
            return_value=plan_data,
        ),
        patch(
            'app.modules.shop_runner.service_manager.'
            'old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.'
            'AdvSettingAutoUpdater.get_fact_data',
             return_value=fact_data
            ),
        patch(
            'app.modules.shop_runner.service_manager.'
            'old_modules.setting_auto_updater_v2.adv_control_system.adv_control_system.'
            'ChangePlanFact.check_equal_in_cache',
            return_value=False,
        ),
        patch('app.modules.shop_runner.'
              'service_manager.old_modules.'
              'setting_auto_updater_v2.adv_control_system.'
              'adv_control_system.sm', return_value=sm_generator),
    ):
        keywords = await complex_adv.get_keywords()
        before_white_list_size = len([kw for kw in keywords if kw.hard_status == 2])

        # container.settings.override(providers.Configuration())
        # container.module_resources.override(providers.Dependency())

        container = di_containner_for_adv_auto_updater_v2


        await control_system_v2.process_adv(complex_adv, force=3)

        container.settings.reset_override()
        container.module_resources.reset_override()
        container.redis_client.reset_override()

    # 5️⃣ Проверяем KeywordSetting
    updated_settings = await postgres_session.execute(select(KeywordSetting))
    updated_settings = updated_settings.scalars().all()
    updated_adv_setting: AdvSetting | None = await postgres_session.get(AdvSetting, complex_adv.adv_setting.id)
    updated_adv_setting = cast(AdvSetting, updated_adv_setting)

    after_white_list_size = len([kw for kw in updated_settings if kw.hard_status == 2])
    assert condition_func(after_white_list_size, before_white_list_size, updated_adv_setting, complex_adv)