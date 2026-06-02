"""Unit-тесты WBAdvDtoSnapshotAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.snapshot_data_updater.config import SnapshotUpdaterConfig


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shadow_log_only_when_enabled() -> None:
    from app.snapshot_data_updater.adapters.wb_adv_dto_adapter import (
        WBAdvDtoSnapshotAdapter,
    )

    adapter = WBAdvDtoSnapshotAdapter(
        config=SnapshotUpdaterConfig(wb_adv_dto_shadow_compare=False)
    )
    adapter.load_snapshot = AsyncMock(return_value=None)
    await adapter.shadow_log_keywords_delta("s1", 1, legacy_count=5)
    adapter.load_snapshot.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shadow_log_swallows_reader_errors() -> None:
    """Сбой shadow не пробрасывается — observability не ломает consumer path."""
    from app.snapshot_data_updater.adapters.wb_adv_dto_adapter import (
        WBAdvDtoSnapshotAdapter,
    )

    reader = AsyncMock()
    reader.get_adv_snapshot = AsyncMock(side_effect=RuntimeError("redis down"))
    adapter = WBAdvDtoSnapshotAdapter(
        reader=reader,
        config=SnapshotUpdaterConfig(wb_adv_dto_shadow_compare=True),
    )

    await adapter.shadow_log_keywords_delta("s1", 7, legacy_count=3)

    reader.get_adv_snapshot.assert_awaited_once()
