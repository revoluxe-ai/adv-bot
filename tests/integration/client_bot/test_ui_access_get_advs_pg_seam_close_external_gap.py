"""Integration coverage for ui_access + WBShopDataManager.__get_advs PG seams.

Live ``async_session`` + re-read. Authored under ``/opsx-close-external-gap``;
do not run live without ``AUTHORIZE_ONE_LIVE_RUN``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.client_bot.ui_access import UiAccessMode, UiAccessResolver
from app.client_bot.ui_mode import UiModeService
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


@pytest.mark.asyncio
async def test_resolve_shop_ui_access_paid_when_bot_active_adv(
    async_session,
) -> None:
    """PURE_READ ui_access resolves PAID when shop has bot_active AdvSetting."""
    shop_id = f"ui_access_{uuid.uuid4().hex[:10]}"
    cabinet = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.utcnow() + timedelta(days=7),
    )
    async_session.add(cabinet)
    await async_session.flush()
    adv = AdvSetting(
        adv_id=771001,
        name="ui-access-paid",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.commit()

    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    resolver = UiAccessResolver(ui_mode_service=UiModeService(redis_client=redis_client))
    access = await resolver.resolve_shop_ui_access(9_999_001, async_session, shop_id)
    assert access == UiAccessMode.PAID


@pytest.mark.asyncio
async def test_wb_shop_data_manager_get_advs_in_session(
    async_session,
) -> None:
    """PURE_READ __get_advs returns AdvSetting rows for shop via injected session."""
    shop_id = f"get_advs_{uuid.uuid4().hex[:10]}"
    cabinet = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.utcnow() + timedelta(days=7),
    )
    async_session.add(cabinet)
    await async_session.flush()
    adv = AdvSetting(
        adv_id=771002,
        name="get-advs",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.commit()

    rows = await WBShopDataManager._WBShopDataManager__get_advs(
        async_session, shop_id, only_bot_active=True
    )
    assert len(rows) == 1
    assert rows[0].adv_id == 771002


@pytest.mark.asyncio
async def test_wb_shop_data_manager_get_adv_id_to_search_adv_map_in_session(
    async_session,
) -> None:
    """PURE_READ __get_adv_id_to_search_adv_map returns rows via injected session."""
    shop_id = f"search_map_{uuid.uuid4().hex[:10]}"
    cabinet = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.utcnow() + timedelta(days=7),
    )
    async_session.add(cabinet)
    await async_session.flush()
    search_adv = AdvSetting(
        adv_id=881001,
        name="search-only",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=False,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(search_adv)
    await async_session.commit()

    mapping = await WBShopDataManager._WBShopDataManager__get_adv_id_to_search_adv_map(
        async_session, {881001, 999999}
    )
    assert set(mapping.keys()) == {881001}
    assert mapping[881001].adv_id == 881001
