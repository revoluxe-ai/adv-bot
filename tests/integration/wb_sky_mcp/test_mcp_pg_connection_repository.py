"""PostgreSQL boundary evidence for ``SqlConnectionRepository`` (MCP connections).

Requires destructive-local gate (localhost test DB). Not executed in cloud CI
without disposable PostgreSQL.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_mcp.connection_repository import SqlConnectionRepository
from app.modules.wb_sky_mcp.models import McpConnection
from app.utils.db.models import User
from tests.support.wb_sky_mcp.connection_repository_contract import (
    CONNECTION_REPOSITORY_CONTRACT_CASES,
    CONTRACT_ID,
    ConnectionRepositoryContractCase,
    run_connection_repository_contract,
    run_persist_add_get_disconnect_version,
    run_refresh_rotation_rejects_reuse,
)

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


async def _seed_user(async_session: AsyncSession) -> User:
    user = User(
        user_telegram_id=int(uuid.uuid4().int % 9_000_000_000) + 1_000_000_000,
        username=f"mcp_pg_{uuid.uuid4().hex[:8]}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    assert user.id is not None
    return user


async def _delete_connection(async_session: AsyncSession, public_id: str) -> None:
    await async_session.execute(
        delete(McpConnection).where(McpConnection.public_id == public_id)
    )
    await async_session.commit()


@pytest.mark.asyncio
async def test_sql_connection_repository_persist_and_raw_select(
    async_session: AsyncSession,
) -> None:
    """Provider boundary: add/save persist columns readable via get and raw SELECT."""
    user = await _seed_user(async_session)
    repo = SqlConnectionRepository(async_session)
    state = await run_persist_add_get_disconnect_version(repo, user_id=user.id)

    stmt = select(McpConnection).where(McpConnection.public_id == state.public_id)
    row = (await async_session.execute(stmt)).scalar_one()
    assert row.user_id == user.id
    assert row.authorization_version == 2
    assert row.revoked_at is not None
    assert row.refresh_token_hash is None

    await _delete_connection(async_session, state.public_id)


@pytest.mark.asyncio
async def test_sql_connection_repository_refresh_rotation_rejects_reuse(
    async_session: AsyncSession,
) -> None:
    """Provider boundary: rotation commits under FOR UPDATE; spent hash cannot win twice."""
    user = await _seed_user(async_session)
    repo = SqlConnectionRepository(async_session)
    public_id = await run_refresh_rotation_rejects_reuse(repo, user_id=user.id)
    await _delete_connection(async_session, public_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    CONNECTION_REPOSITORY_CONTRACT_CASES,
    ids=[c.case_id for c in CONNECTION_REPOSITORY_CONTRACT_CASES],
)
async def test_sql_connection_repository_contract_cases(
    async_session: AsyncSession,
    case: ConnectionRepositoryContractCase,
) -> None:
    """Shared ContractCase vectors against live ``SqlConnectionRepository``."""
    user = await _seed_user(async_session)
    repo = SqlConnectionRepository(async_session)
    public_id = await run_connection_repository_contract(
        repo, case, user_id=user.id
    )
    if public_id is not None:
        await _delete_connection(async_session, public_id)

    assert CONTRACT_ID
