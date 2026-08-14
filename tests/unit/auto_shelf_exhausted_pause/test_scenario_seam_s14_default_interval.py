"""Scenario seam S14: get_or_create_settings applies product default interval=7."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    AutoShelfBidControlRepository,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s14_get_or_create_settings_applies_default_retest_interval_seven() -> None:
    """S14: production create path sets retest_interval_days=7 (not constant-only)."""
    assert DEFAULT_RETEST_INTERVAL_DAYS == 7
    repo = AutoShelfBidControlRepository()
    session = MagicMock()
    created_objs: list[object] = []

    def _add(obj: object) -> None:
        created_objs.append(obj)

    session.add = _add
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo.get_settings_in_session = AsyncMock(return_value=None)  # type: ignore[method-assign]

    created = await repo.get_or_create_settings_in_session(
        session,  # type: ignore[arg-type]
        nmid=42_001,
        default_max_bid_minor=50_000,
        currency="RUB",
    )

    assert created_objs, "settings object must be session.add'd on create path"
    assert created.retest_interval_days == 7
    assert created.retest_interval_days == DEFAULT_RETEST_INTERVAL_DAYS
    assert created.nmid == 42_001
    session.flush.assert_awaited()
