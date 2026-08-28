# tests/test_start.py

import pytest
from app.client_bot.user_interface.handlers.start.start import __get_wb_user_cabinet
from app.modules.common_slaves.wildberries.models.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.adv_factory import WBUserCabinetFactory


@pytest.mark.integration
@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_get_wb_user_cabinet_success(async_session: AsyncSession):
    # Mock data

    wb_user_cabinet_mock: WBUserCabinet = WBUserCabinetFactory.build()
    async_session.add(wb_user_cabinet_mock)
    await async_session.flush()

    wb_user_cabinet: WBUserCabinet = await __get_wb_user_cabinet(session=async_session,
                                                                 user_id=wb_user_cabinet_mock.user_id,
                                                                 shop_id=wb_user_cabinet_mock.wb_cabinet.shop_id)

    assert wb_user_cabinet.user_id == wb_user_cabinet_mock.user_id
    assert wb_user_cabinet.wb_cabinet.shop_id == wb_user_cabinet_mock.wb_cabinet.shop_id
    return None

