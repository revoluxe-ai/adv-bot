"""Mock-only handoff proofs for CPM target-place workbook PG seams."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.services import cpm_target_place_workbook as workbook

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return cm


async def test_build_workbook_parent_passes_session_read_only() -> None:
    """build_target_place_workbook uses sm(read_only=True) → child(session)."""
    session = AsyncMock(spec=AsyncSession)
    keyword = MagicMock()
    keyword.id = 1
    keyword.text = "alpha"
    keyword.target_place = 3

    with (
        patch.object(workbook, "_sm", _session_cm(session)),
        patch.object(
            workbook,
            "load_keywords_for_target_place_workbook_in_session",
            new_callable=AsyncMock,
            return_value=[keyword],
        ) as load_mock,
        patch.object(
            workbook,
            "write_target_place_workbook_rows",
            return_value=b"xlsx",
        ),
    ):
        content = await workbook.build_target_place_workbook(99)

    assert content == b"xlsx"
    load_mock.assert_awaited_once_with(session, 99)


async def test_apply_workbook_parent_passes_session_write() -> None:
    """apply_target_place_workbook uses sm(read_only=False) → child(session)."""
    session = AsyncMock(spec=AsyncSession)
    summary = workbook.TargetPlaceImportSummary(processed_rows=1)

    with (
        patch.object(workbook, "_sm", _session_cm(session)),
        patch.object(
            workbook,
            "read_target_place_workbook",
            return_value=[{"keyword_id": 1, "target_place": 2}],
        ),
        patch.object(
            workbook,
            "_verify_adv_owner_in_session",
            new_callable=AsyncMock,
        ),
        patch.object(
            workbook,
            "apply_target_place_rows_in_session",
            new_callable=AsyncMock,
            return_value=summary,
        ) as apply_mock,
    ):
        result = await workbook.apply_target_place_workbook(
            55, b"bytes", telegram_user_id=9001
        )

    assert result is summary
    apply_mock.assert_awaited_once()
    args = apply_mock.await_args
    assert args is not None
    assert args.args[0] is session
    assert args.args[1] == 55
    assert args.kwargs["telegram_user_id"] == 9001
