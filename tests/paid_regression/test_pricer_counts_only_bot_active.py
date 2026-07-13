"""Paid regression: pricer учитывает только bot_active кампании."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.pricer.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting
from tests.factories.adv_factory import WBCabinetFactory

pytestmark = [pytest.mark.integration, pytest.mark.paid_regression, pytest.mark.asyncio]


@pytest.mark.asyncio
async def test_pricer_tariff_counts_only_bot_active_advs(
    async_session: AsyncSession,
) -> None:
    wb_cabinet = WBCabinetFactory.build(
        id=1,
        shop_id="shop-1",
        active=True,
        balance=0.0,
        bonus=0.0,
        demo=True,
    )
    active_adv = AdvSetting(
        adv_id=1001,
        name="active_auto",
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        active_status="started",
        _search_adv_id=9001,  # noqa: SLF001
        automatic_version=2,
        auto_update_white_list=True,
        auto_update_target_place=False,
    )
    inactive_adv = AdvSetting(
        adv_id=1002,
        name="inactive_auto",
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,
        active_status="started",
        _search_adv_id=9002,  # noqa: SLF001
        automatic_version=2,
        auto_update_white_list=True,
        auto_update_target_place=False,
    )
    async_session.add_all([wb_cabinet, active_adv, inactive_adv])
    await async_session.flush()

    details = await Pricer().get_tariff_details(session=async_session, shop_id="shop-1")

    assert details.count == 1
    assert details.total_per_month > 0.0
