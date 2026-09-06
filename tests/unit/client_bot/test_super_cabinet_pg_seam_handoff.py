"""Mock-only handoff proofs for super_cabinet_manager PG seams."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries import super_cabinet_manager

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _build_sm_context(session: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _session_cm(session: MagicMock):
    """Собрать async contextmanager для mock `sm` с записью вызова."""
    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[MagicMock, None]:
        yield session

    return cm


async def test_get_access_parent_handoff_to_children_for_shop_id() -> None:
    """get_access_for_wb_cabinet resolves id then loads access via injected sessions."""
    shop_id = "shop-handoff"
    session1 = MagicMock()
    session2 = MagicMock()
    access = super_cabinet_manager.WBCabinetAccess(
        tokens=[MagicMock()], wb_user_cabinet=None, wb_cabinet=MagicMock()
    )

    with (
        patch.object(
            super_cabinet_manager,
            "sm",
            side_effect=[_build_sm_context(session1), _build_sm_context(session2)],
        ) as sm_mock,
        patch.object(
            super_cabinet_manager,
            "resolve_wb_cabinet_id_by_shop_id_in_session",
            new_callable=AsyncMock,
            return_value=321,
        ) as resolve_mock,
        patch.object(
            super_cabinet_manager,
            "load_wb_cabinet_access_in_session",
            new_callable=AsyncMock,
            return_value=access,
        ) as load_mock,
    ):
        result = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)

    assert result is access
    resolve_mock.assert_awaited_once_with(session1, shop_id)
    load_mock.assert_awaited_once_with(session2, 321)
    assert sm_mock.call_args_list[0].kwargs.get("read_only") is True
    assert sm_mock.call_args_list[1].kwargs.get("read_only") is False


async def test_get_access_deactivate_path_uses_write_session() -> None:
    """Missing personal tokens: child returns shop_id; parent deactivates."""
    session = MagicMock()
    with (
        patch.object(
            super_cabinet_manager,
            "sm",
            return_value=_build_sm_context(session),
        ),
        patch.object(
            super_cabinet_manager,
            "load_wb_cabinet_access_in_session",
            new_callable=AsyncMock,
            return_value="shop-x",
        ),
        patch.object(
            super_cabinet_manager,
            "deactivate_cabinet_atomic_with_user_trackers",
            new_callable=AsyncMock,
        ) as deactivate_mock,
    ):
        with pytest.raises(ApiForbiddenError):
            await super_cabinet_manager.get_access_for_wb_cabinet(999)

    deactivate_mock.assert_awaited_once()


async def test_get_common_access_parent_hands_off_session_to_child() -> None:
    """get_common_access opens sm(read_only=True) and hands session to child."""
    session = MagicMock()
    client_session = MagicMock()
    token = MagicMock(spec=super_cabinet_manager.WBToken)
    sm_mock = MagicMock(side_effect=_session_cm(session))

    with (
        patch.object(super_cabinet_manager, "sm", sm_mock),
        patch.object(
            super_cabinet_manager,
            "find_common_access_token_in_session",
            new_callable=AsyncMock,
            return_value=token,
        ) as find_mock,
    ):
        result = await super_cabinet_manager.get_common_access(client_session)

    assert result.tokens == [token]
    find_mock.assert_awaited_once_with(session, client_session)
    assert sm_mock.call_args is not None
    assert sm_mock.call_args.kwargs.get("read_only") is True
