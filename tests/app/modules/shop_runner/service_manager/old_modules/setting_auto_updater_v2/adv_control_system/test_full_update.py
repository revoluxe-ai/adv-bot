
from typing import cast

import pytest
from unittest.mock import patch, AsyncMock

from dependency_injector import providers
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
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

pytestmark = pytest.mark.destructive_local
@pytest.mark.parametrize("plan_data,fact_data,condition_func",
                    [
                        (PlanData(orders=15, target_pay_for_order=120,max_pay_for_order=300,), #  Мало продаж - большой расход
                    FactData(predict_orders=10.0, pay_for_order=500.0, original_orders=10,
                                 fact_method=FactMethods.DIRECT_SALES,),
                        lambda new_white_list_size, white_list_size, updated_adv_setting, initial_target_place, initial_exponent: \
                    any([new_white_list_size < white_list_size,
                     updated_adv_setting.max_place > initial_target_place,
                     updated_adv_setting.exponent_predict_ctr > initial_exponent],
                                 )
                         ),
                     (PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж больше чем надо и расход больше максимального
                      FactData(predict_orders=30, pay_for_order=250.0, original_orders=10,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, initial_target_place, initial_exponent: \
                              any([new_white_list_size < white_list_size,
                                   updated_adv_setting.max_place > initial_target_place,
                                   updated_adv_setting.exponent_predict_ctr > initial_exponent],
                                  )),
                     (PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж больше чем надо и расход больше максимального
                      FactData(predict_orders=30, pay_for_order=250.0, original_orders=10,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, initial_target_place, initial_exponent: \
                              any([new_white_list_size < white_list_size,
                                   updated_adv_setting.max_place > initial_target_place,
                                   updated_adv_setting.exponent_predict_ctr > initial_exponent],
                                  )),
                     (

                    PlanData(orders=15, target_pay_for_order=120, max_pay_for_order=300, ), # Продаж мало, расход меньше максимального
                      FactData(predict_orders=1, pay_for_order=50, original_orders=1,
                               fact_method=FactMethods.DIRECT_SALES, ),
                      lambda new_white_list_size, white_list_size, updated_adv_setting, initial_target_place, initial_exponent: \
                              any([new_white_list_size > white_list_size,
                                   updated_adv_setting.max_place < initial_target_place,
                                   updated_adv_setting.exponent_predict_ctr < initial_exponent],
                                  ) and not any ([new_white_list_size < white_list_size,
                                  updated_adv_setting.max_place > initial_target_place,
                                  updated_adv_setting.exponent_predict_ctr > initial_exponent])

                      ),])
@pytest.mark.asyncio(scope='function')
async def test_process_adv(postgres_session: AsyncSession,
                        complex_adv: ComplexAdv,
                           plan_data,
                           fact_data,
                           condition_func,
                           sm_generator,
                           app_container,
                           fake_redis
                           ):
    """Интеграционный тест для AdvControlSystem.process_adv с фейковыми данными."""

    control_system_v2 = AdvControlSystem(max_last_period=2)


    # 3️⃣ ComplexAdv мок (теперь с нормальной фабрикой)
    # 4️⃣ Мокаем план и факт

    initial_target_place = complex_adv.adv_setting.max_place # Сохраняем начальное значение
    initial_exponent = complex_adv.adv_setting.exponent_predict_ctr # Сохраняем начальное значение

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
        patch(
            'app.modules.shop_runner.service_manager.'
            'old_modules.setting_auto_updater_v2.adv_control_system.'
            'executors.target_place_executor.utils.get_max_cpm',
            new=AsyncMock(return_value=400),
        ),
    ):
        keywords = await complex_adv.get_keywords()
        before_white_list_size = len([kw for kw in keywords if kw.hard_status == 2])
        complex_adv.get_mean_auto_ctr = AsyncMock(return_value=3.0)

        app_container.redis_client.override(providers.Object(fake_redis))

        await control_system_v2.process_adv(complex_adv, force=3)
        app_container.redis_client.reset_override()
    # 5️⃣ Проверяем KeywordSetting
    updated_settings = await postgres_session.execute(select(KeywordSetting))
    updated_settings = updated_settings.scalars().all()
    updated_adv_setting: AdvSetting | None = await postgres_session.get(AdvSetting, complex_adv.adv_setting.id)
    updated_adv_setting = cast(AdvSetting, updated_adv_setting)

    after_white_list_size = len([kw for kw in updated_settings if kw.hard_status == 2])

    # complex_adv.adv_setting.max_place = initial_target_place # Убираем ручное восстановление
    # complex_adv.adv_setting.exponent_predict_ctr = initial_exponent # Убираем ручное восстановление

    """
    TODO: Улучшение теста test_process_adv

1. Убрать ручное сохранение и восстановление значений initial_target_place / initial_exponent.
2. Переделать фикстуру complex_adv так, чтобы она создавалась изолированно и @pytest.fixture(scope="function") 
   всегда возвращала новый объект с чистым состоянием.
3. Переписать condition_func так, чтобы он не использовал complex_adv, а сравнивал updated_adv_setting 
   с initial значениями, переданными явно.
4. Переработать структуру теста в стиле Arrange–Act–Assert для повышения читаемости.
5. Перестать передавать сам complex_adv внутрь condition_func — заменив на чистые входные данные.
6. (Опционально) Вынести condition_func в именованные функции для лучшей читаемости.
    
    """

    assert condition_func(after_white_list_size, before_white_list_size, updated_adv_setting, initial_target_place, initial_exponent)
