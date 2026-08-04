"""Integration tests for shop menu data loading helpers.

Требуют ``destructive_local``: используют fixture ``async_session`` (live PG).
"""

import pytest

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User


pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def test_get_wb_user_cabinet_with_user_and_wb_cabinet_loads_relations(
    async_session,
) -> None:
    """Load WBUserCabinet together with related user and wb_cabinet."""
    user = User(
        user_telegram_id=990001,
        username="shop_menu_test_user",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()

    wb_cabinet = WBCabinet(
        shop_id="shop_menu_test_shop",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=wb_cabinet.id,
        name="Shop Menu Test Shop",
    )
    async_session.add(wb_user_cabinet)
    await async_session.commit()

    result = await ShopMenu._get_wb_user_cabinet_with_user_and_wb_cabinet(
        async_session,
        wb_user_cabinet.id,
    )

    assert result.id == wb_user_cabinet.id
    assert result.user is not None
    assert result.user.id == user.id
    assert result.user.user_telegram_id == user.user_telegram_id
    assert result.wb_cabinet is not None
    assert result.wb_cabinet.id == wb_cabinet.id
    assert result.wb_cabinet.shop_id == wb_cabinet.shop_id
