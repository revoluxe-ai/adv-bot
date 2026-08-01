"""Live-PG тесты фильтра AdvSetting по wb_cabinet / bot_active в ShopDataUpdater.

Требуют ``destructive_local``: используют fixture ``async_session``.
"""

from typing import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from tests.factories import AdvSettingFactory, WBCabinetFactory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def test_get_adv_setting_by_wb_cabinet_active_filter(
    async_session: AsyncSession,
):
    """bot_active=True попадает в выборку get_adv_setting_by_wb_cabinet_active_filter."""
    wb_cabinet = WBCabinetFactory.build()

    adv_setting = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet,
        bot_active=True,
    )
    try:
        async_session.add(adv_setting)
        await async_session.flush()
        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet_active_filter(
                async_session,
                wb_cabinet_id=wb_cabinet.id,
            )
        )
        assert adv_settings

    finally:
        await async_session.rollback()


async def test_get_adv_setting_by_wb_cabinet_active_filter_not_bot_active(
    async_session: AsyncSession,
):
    """bot_active=False исключается при only_bot_active=True."""
    wb_cabinet = WBCabinetFactory.build()

    adv_setting = AdvSettingFactory.build(
        wb_cabinet=wb_cabinet,
        bot_active=False,
    )
    try:
        async_session.add(adv_setting)
        await async_session.flush()
        adv_settings: Sequence[AdvSetting] = (
            await ShopDataUpdater.get_adv_setting_by_wb_cabinet_active_filter(
                async_session,
                wb_cabinet_id=wb_cabinet.id,
                only_bot_active=True,
            )
        )
        assert not adv_settings

    finally:
        await async_session.rollback()
