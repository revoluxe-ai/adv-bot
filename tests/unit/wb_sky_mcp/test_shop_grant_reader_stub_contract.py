"""Stub contract: ``MemoryShopGrantReader`` matches grant list shape."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_mcp.grants import MemoryShopGrantReader, ShopGrant
from tests.support.wb_sky_mcp.shop_grant_contract import (
    CONTRACT_ID,
    ShopGrantContractCase,
    run_shop_grant_contract,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_memory_shop_grant_reader_contract_shape() -> None:
    """Pre-seeded memory rows expose the same ShopGrant fields SQL returns."""
    case = ShopGrantContractCase(
        case_id="memory_rows",
        user_id=7,
        expected_shop_ids=("111", "222"),
    )
    reader = MemoryShopGrantReader(
        {
            7: [
                ShopGrant(shop_id="111", name="A", active=True),
                ShopGrant(shop_id="222", name="B", active=False),
            ],
        }
    )
    await run_shop_grant_contract(reader, case)
    assert await reader.list_shops(99) == []
    assert CONTRACT_ID
