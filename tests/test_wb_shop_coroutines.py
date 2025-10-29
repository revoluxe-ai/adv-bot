from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager import CoroutinesManager
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
    FactData,
)


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
    session.close = MagicMock()
    return session


@pytest.mark.parametrize(
    "fact_method",
    [
        FactMethods.DIRECT_SALES,
        FactMethods.BY_CARTS,
    ],
)
@pytest.mark.asyncio
async def test_adv_settings_auto_update(
    access_mock, adv_setting_mock, keywords_mocks, client_session_mock, fact_method
):
    wb_api = WBApi(access_mock, client_session_mock)

    data_manager_mock = MagicMock()
    data_manager_mock.get_good_bad_phrases = AsyncMock(return_value=keywords_mocks)
    plan_data = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=250)

    fact_data = FactData(
        predict_orders=1, pay_for_order=100, original_orders=1, fact_method=fact_method
    )
    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.data_manager",
            new=data_manager_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.AdvSettingAutoUpdater.get_fact_data",
            new=AsyncMock(return_value=fact_data),
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            new=MagicMock(return_value=plan_data),
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_active_advs",
            new=AsyncMock(return_value=[adv_setting_mock]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.WBShopDataManager.get_calculated_keywords",
            new=AsyncMock(return_value=keywords_mocks),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater.AdvSettingAutoUpdater.update",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager.delete_last_white_phrase",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager.delete_last_white_phrase"
        ),
    ):
        manager = CoroutinesManager(wb_api)
        manager._update_advs_models = AsyncMock()
        manager._adv_settings_list = [adv_setting_mock]
        manager._adv_settings_dict = {adv_setting_mock.adv_id: adv_setting_mock}
        # decorator while_coroutine_decorator запускает корутину в бесконечном цикле,
        # поэтому в тестах мы вызываем оригинальную функцию через __wrapped__,
        # чтобы выполнить её один раз и не зависнуть.
        await manager.adv_settings_auto_update.__wrapped__(manager)
