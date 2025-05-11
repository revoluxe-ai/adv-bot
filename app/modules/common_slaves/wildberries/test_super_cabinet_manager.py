import pytest

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "shop_id",
    [
        "7de14a75-4939-40ff-b4dd-9dd5472a4348",
    ],
)
async def test_super_cabinet_manager_get_access_for_wb_cabinet(shop_id):
    access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
    assert isinstance(access, WBCabinetAccess)
