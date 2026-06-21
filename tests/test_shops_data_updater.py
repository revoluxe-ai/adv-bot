import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession


from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from tests.factories import AdvSettingFactory, WBCabinetFactory



@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_adv_setting_by_wb_cabinet_active_filter(
    async_session: AsyncSession,
):

    wb_cabinet = WBCabinetFactory.build(
    )

    adv_setting = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet

    )
    try:
        async_session.add(adv_setting)
        await async_session.flush()
        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet_active_filter(
                async_session,
                wb_cabinet.id,
            )
        )
        assert adv_settings

    finally:
        await async_session.rollback()
