import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession


from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from tests.app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.first_key_updater.test_first_key_updater import \
    adv_setting
from tests.factories import AdvSettingFactory, WBCabinetFactory



@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_adv_setting_by_wb_cabinet_active_filter(
    async_session: AsyncSession,
):

    wb_cabinet = WBCabinetFactory.build(
    )

    adv_setting = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet,
        bot_active=True

    )
    try:
        async_session.add(adv_setting)
        await async_session.flush()
        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet_with_search_adv_id(
                async_session,
                wb_cabinet_id=wb_cabinet.id,
            )
        )
        assert adv_settings

    finally:
        await async_session.rollback()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_adv_setting_by_wb_cabinet_with_search_adv_id(
    async_session: AsyncSession,
):
    """AdvSetting._search_adv_id - признак полноценной ComplexAdv"""
    wb_cabinet_id = 1_000_000_0
    wb_cabinet = WBCabinetFactory.build(
        id=1_000_000_0
    )
    adv_setting_id_1 = 1_000_000_1
    adv_setting_1 = AdvSettingFactory.build(
        id=adv_setting_id_1,
        wb_cabinet=wb_cabinet,
        bot_active=True,
        _search_adv_id=None,
    )

    adv_setting_id_2 = 1_000_000_2
    adv_setting_2 = AdvSettingFactory.build(
        id=adv_setting_id_2,
        wb_cabinet=wb_cabinet,
        bot_active=False,
        _search_adv_id=2,
    )
    try:
        async_session.add(adv_setting_1)
        async_session.add(adv_setting_2)
        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet_with_search_adv_id(
                async_session,
                wb_cabinet_id=wb_cabinet_id,
            )
        )
        assert len([adv for adv in adv_settings if adv.id == adv_setting_id_1 and adv._search_adv_id == 1]) == 0
        assert  len([adv for adv in adv_settings if adv.id == adv_setting_id_2 and adv._search_adv_id == 2]) == 1

    finally:
        await async_session.rollback()

