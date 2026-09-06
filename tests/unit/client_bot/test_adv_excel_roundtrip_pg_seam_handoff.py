"""Mock-only handoff proof for adv Excel export PG seam."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.services.adv_excel_roundtrip import export_build

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return cm


async def test_build_adv_excel_export_parent_hands_off_session() -> None:
    """build_adv_excel_export opens sm(read_only=True) and hands session to child."""
    session = AsyncMock(spec=AsyncSession)
    sm_mock = MagicMock(side_effect=_session_cm(session))
    with (
        patch.object(export_build, "_sm", sm_mock),
        patch.object(
            export_build,
            "build_adv_excel_export_in_session",
            new_callable=AsyncMock,
            return_value=(["h"], [{"row": 1}]),
        ) as child_mock,
    ):
        result = await export_build.build_adv_excel_export(
            wb_user_cabinet_id=77,
            progress_callback=None,
        )

    assert result == (["h"], [{"row": 1}])
    child_mock.assert_awaited_once_with(
        session,
        wb_user_cabinet_id=77,
        progress_callback=None,
    )
    assert sm_mock.call_args is not None
    assert sm_mock.call_args.kwargs.get("read_only") is True
