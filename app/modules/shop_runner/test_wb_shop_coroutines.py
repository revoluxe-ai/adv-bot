from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.modules.wb_api import WBApi
from .service_manager.manager import CoroutinesManager
from .service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)


@pytest.mark.asyncio
async def test_adv_settings_auto_update(access_mock, adv_setting_mock, keywords_mocks):
    wb_api = WBApi(access_mock)

    data_manager_mock = MagicMock()
    data_manager_mock.get_good_bad_phrases = AsyncMock(return_value=keywords_mocks)
    plan_data = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=250)

    fact_data = FactData(predict_orders=1, pay_for_order=100)
    with (
        patch(
            "app.modules.shop_runner.coroutine_manager.manager.data_manager",
            new=data_manager_mock,
        ),
        patch(
            "app.modules.shop_runner.coroutine_manager.manager.AdvSettingAutoUpdater.get_fact_data",
            new=AsyncMock(return_value=fact_data),
        ),
        patch(
            "app.modules.shop_runner.coroutine_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            new=MagicMock(return_value=plan_data),
        ),
        patch(
            "app.modules.shop_runner.coroutine_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager._delete_phrase_from_white_list",
            new_callable=AsyncMock,
        ) as delete_phrase_from_white_list_method,
        patch(
            "app.modules.shop_runner.coroutine_manager.old_modules.setting_auto_updater.modules.white_list_updater."
            "auto_white_list_updater.auto_white_list_updater.WhiteListUpdateManager._delete_phrase_from_white_list"
        ),
    ):
        manager = CoroutinesManager(wb_api)
        manager._update_advs_models = AsyncMock()
        manager._adv_settings_list = [adv_setting_mock]
        manager._adv_settings_dict = {adv_setting_mock.adv_id: adv_setting_mock}
        await manager.adv_settings_auto_update()
