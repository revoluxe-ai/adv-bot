"""Unit tests for UI mode helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.ui_mode import UiModeService, get_ui_mode_redis_key

pytestmark = pytest.mark.unit


def test_ui_mode_redis_key_builder() -> None:
    assert get_ui_mode_redis_key(123) == "ui_mode:user:123"


@pytest.mark.asyncio
async def test_default_ui_mode_for_regular_user_is_free() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    service = UiModeService(redis_client=redis_client)

    assert await service.get_user_ui_mode(999999) == "free"


@pytest.mark.asyncio
async def test_default_ui_mode_for_admin_is_paid() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    service = UiModeService(redis_client=redis_client)

    assert await service.get_user_ui_mode(373435337) == "paid"


@pytest.mark.asyncio
async def test_toggle_ui_mode_persists_value() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="paid")
    redis_client.set = AsyncMock(return_value=True)
    service = UiModeService(redis_client=redis_client)

    assert await service.toggle_user_ui_mode(373435337) == "free"
    redis_client.set.assert_awaited_once_with("ui_mode:user:373435337", "free")


@pytest.mark.asyncio
async def test_should_show_paid_controls_for_admin_paid_mode() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="paid")
    service = UiModeService(redis_client=redis_client)

    assert await service.should_show_paid_controls(373435337) is True


@pytest.mark.asyncio
async def test_should_show_paid_controls_for_admin_free_mode() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="free")
    service = UiModeService(redis_client=redis_client)

    assert await service.should_show_paid_controls(373435337) is False


@pytest.mark.asyncio
async def test_should_show_paid_controls_for_regular_user_is_false() -> None:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="paid")
    service = UiModeService(redis_client=redis_client)

    assert await service.should_show_paid_controls(999999) is False
