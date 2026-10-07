"""PostgreSQL boundary evidence for ``SqlShopGrantReader.list_shops``."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_sky_mcp.grants import SqlShopGrantReader
from app.utils.db.models import User
from tests.support.wb_sky_mcp.shop_grant_contract import (
    CONTRACT_ID,
    ShopGrantContractCase,
    assert_shop_grants_match,
    run_shop_grant_contract,
)

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


async def _seed_user(async_session: AsyncSession, *, suffix: str) -> User:
    user = User(
        user_telegram_id=int(uuid.uuid4().int % 9_000_000_000) + 1_000_000_000,
        username=f"mcp_grant_{suffix}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    assert user.id is not None
    return user


async def _link_cabinet(
    async_session: AsyncSession,
    *,
    user: User,
    shop_id: str,
    name: str,
    active: bool,
) -> WBUserCabinet:
    wb_cabinet = WBCabinet(
        shop_id=shop_id,
        active=active,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()
    link = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=wb_cabinet.id,
        name=name,
    )
    async_session.add(link)
    await async_session.flush()
    return link


@pytest.mark.asyncio
async def test_sql_shop_grant_reader_lists_only_principal_cabinets(
    async_session: AsyncSession,
) -> None:
    """Provider boundary: grants follow ``WBUserCabinet`` rows for the given User.id."""
    target = await _seed_user(async_session, suffix="target")
    foreign = await _seed_user(async_session, suffix="foreign")
    shop_id = f"mcp_shop_{uuid.uuid4().hex[:10]}"
    await _link_cabinet(
        async_session,
        user=target,
        shop_id=shop_id,
        name="Target cabinet",
        active=True,
    )
    await _link_cabinet(
        async_session,
        user=foreign,
        shop_id=f"other_{uuid.uuid4().hex[:10]}",
        name="Foreign cabinet",
        active=True,
    )
    await async_session.flush()

    reader = SqlShopGrantReader(async_session)
    case = ShopGrantContractCase(
        case_id="scoped_shop_list",
        user_id=target.id,
        expected_shop_ids=(shop_id,),
    )
    await run_shop_grant_contract(reader, case)

    foreign_grants = await reader.list_shops(foreign.id)
    assert [g.shop_id for g in foreign_grants] != [shop_id]

    assert CONTRACT_ID


@pytest.mark.asyncio
async def test_sql_shop_grant_reader_empty_grant_is_success(
    async_session: AsyncSession,
) -> None:
    """Empty cabinet list is a successful read, not an error."""
    user = await _seed_user(async_session, suffix="empty")
    reader = SqlShopGrantReader(async_session)
    grants = await reader.list_shops(user.id)
    assert_shop_grants_match(grants, expected_shop_ids=())
