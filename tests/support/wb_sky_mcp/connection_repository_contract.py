"""Executable ContractCase vectors for MCP connection repository parity.

Memory and ``SqlConnectionRepository`` must agree on add/get/save, disconnect
versioning, and refresh rotation semantics (including reuse rejection).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pytest

from app.modules.wb_sky_mcp.connection_logic import (
    McpConnectionState,
    disconnect,
    hash_refresh_token,
    rotate_refresh,
    store_refresh,
)
from app.modules.wb_sky_mcp.connection_repository import ConnectionRepository
from app.modules.wb_sky_mcp.errors import McpError

CONTRACT_ID = "wb_sky_mcp.connection_repository.pg_boundary.v1"

_FIXED_NOW = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=datetime.timezone.utc)
_REFRESH_TTL = 3600


@dataclass(frozen=True)
class ConnectionRepositoryContractCase:
    """One named invariant shared by memory and SQL adapters."""

    case_id: str


CONNECTION_REPOSITORY_CONTRACT_CASES: tuple[ConnectionRepositoryContractCase, ...] = (
    ConnectionRepositoryContractCase(case_id="persist_add_get_disconnect_version"),
    ConnectionRepositoryContractCase(case_id="refresh_rotation_rejects_reuse"),
)


async def run_persist_add_get_disconnect_version(
    repo: ConnectionRepository,
    *,
    user_id: int,
) -> McpConnectionState:
    """Persist a row, read back, disconnect with version bump."""
    state = McpConnectionState.create(user_id, now=_FIXED_NOW)
    await repo.add(state)

    loaded = await repo.get(state.public_id)
    assert loaded is not None
    assert loaded.public_id == state.public_id
    assert loaded.user_id == user_id
    assert loaded.authorization_version == 1
    assert loaded.revoked_at is None
    assert loaded.refresh_token_hash is None

    token = "contract-refresh-token"
    store_refresh(state, token, now=_FIXED_NOW, ttl_seconds=_REFRESH_TTL)
    await repo.save(state)
    after_refresh = await repo.get(state.public_id)
    assert after_refresh is not None
    assert after_refresh.refresh_token_hash == hash_refresh_token(token)

    disconnect(state, now=_FIXED_NOW + datetime.timedelta(seconds=5))
    await repo.save(state)
    revoked = await repo.get(state.public_id)
    assert revoked is not None
    assert revoked.authorization_version == 2
    assert revoked.revoked_at is not None
    assert revoked.refresh_token_hash is None
    return state


async def run_refresh_rotation_rejects_reuse(
    repo: ConnectionRepository,
    *,
    user_id: int,
) -> str:
    """Rotation succeeds once; presenting the spent hash again must not succeed."""
    state = McpConnectionState.create(user_id, now=_FIXED_NOW)
    presented = "presented-refresh-a"
    store_refresh(state, presented, now=_FIXED_NOW, ttl_seconds=_REFRESH_TTL)
    await repo.add(state)

    presented_hash = hash_refresh_token(presented)

    def _rotate_once(current: McpConnectionState) -> str:
        return rotate_refresh(
            current,
            presented,
            now=_FIXED_NOW + datetime.timedelta(seconds=1),
            ttl_seconds=_REFRESH_TTL,
        )

    first = await repo.apply_refresh_rotation(presented_hash, _rotate_once)
    assert first is not None
    _, fresh_token = first
    assert fresh_token

    with pytest.raises(McpError):
        await repo.apply_refresh_rotation(
            presented_hash,
            lambda current: rotate_refresh(
                current,
                presented,
                now=_FIXED_NOW + datetime.timedelta(seconds=2),
                ttl_seconds=_REFRESH_TTL,
            ),
        )

    after_reuse = await repo.get(state.public_id)
    assert after_reuse is not None
    assert after_reuse.revoked_at is not None
    assert after_reuse.authorization_version >= 2
    return state.public_id


async def run_connection_repository_contract(
    repo: ConnectionRepository,
    case: ConnectionRepositoryContractCase,
    *,
    user_id: int,
) -> str | None:
    """Dispatch a ContractCase; return ``public_id`` when a row was created."""
    if case.case_id == "persist_add_get_disconnect_version":
        state = await run_persist_add_get_disconnect_version(repo, user_id=user_id)
        return state.public_id
    if case.case_id == "refresh_rotation_rejects_reuse":
        return await run_refresh_rotation_rejects_reuse(repo, user_id=user_id)
    raise AssertionError(f"unknown contract case: {case.case_id}")
