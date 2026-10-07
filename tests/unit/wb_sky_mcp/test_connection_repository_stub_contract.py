"""Stub contract: memory ``ConnectionRepository`` satisfies shared ContractCase."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_mcp.connection_repository import MemoryConnectionRepository
from tests.support.wb_sky_mcp.connection_repository_contract import (
    CONNECTION_REPOSITORY_CONTRACT_CASES,
    CONTRACT_ID,
    ConnectionRepositoryContractCase,
    run_connection_repository_contract,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    CONNECTION_REPOSITORY_CONTRACT_CASES,
    ids=[c.case_id for c in CONNECTION_REPOSITORY_CONTRACT_CASES],
)
async def test_memory_connection_repository_contract_parity(
    case: ConnectionRepositoryContractCase,
) -> None:
    """Memory adapter must match SQL ContractCase semantics (no PostgreSQL)."""
    repo = MemoryConnectionRepository()
    await run_connection_repository_contract(repo, case, user_id=42)
    assert CONTRACT_ID
