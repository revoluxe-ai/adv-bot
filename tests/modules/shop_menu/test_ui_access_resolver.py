"""Unit tests for UI access resolvers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.ui_access import UiAccessMode, UiAccessResolver
from app.client_bot.ui_mode import UiModeService

pytestmark = pytest.mark.unit


def _resolver(redis_mode: str | None = None) -> UiAccessResolver:
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=redis_mode)
    return UiAccessResolver(ui_mode_service=UiModeService(redis_client=redis_client))


@pytest.mark.asyncio
async def test_shop_resolver_non_admin_without_paid_adv_is_free() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(first=lambda: None))

    access = await _resolver().resolve_shop_ui_access(999999, session, "shop_1")

    assert access == UiAccessMode.FREE


@pytest.mark.asyncio
async def test_shop_resolver_non_admin_with_paid_adv_is_paid() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(first=lambda: object()))

    access = await _resolver().resolve_shop_ui_access(999999, session, "shop_1")

    assert access == UiAccessMode.PAID


@pytest.mark.asyncio
async def test_shop_resolver_mixed_shop_is_paid() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(first=lambda: object()))

    access = await _resolver().resolve_shop_ui_access(999999, session, "shop_1")

    assert access == UiAccessMode.PAID


@pytest.mark.asyncio
async def test_shop_resolver_admin_respects_ui_mode_free() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(first=lambda: object()))

    access = await _resolver("free").resolve_shop_ui_access(373435337, session, "shop_1")

    assert access == UiAccessMode.FREE


@pytest.mark.asyncio
async def test_shop_resolver_admin_respects_ui_mode_paid() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(first=lambda: None))

    access = await _resolver("paid").resolve_shop_ui_access(373435337, session, "shop_1")

    assert access == UiAccessMode.PAID


@pytest.mark.asyncio
async def test_adv_resolver_non_admin_free_adv() -> None:
    adv = SimpleNamespace(bot_active=False)
    access = await _resolver().resolve_adv_ui_access(999999, adv)
    assert access == UiAccessMode.FREE


@pytest.mark.asyncio
async def test_adv_resolver_non_admin_paid_adv() -> None:
    adv = SimpleNamespace(bot_active=True)
    access = await _resolver().resolve_adv_ui_access(999999, adv)
    assert access == UiAccessMode.PAID


@pytest.mark.asyncio
async def test_adv_resolver_admin_free_override() -> None:
    adv = SimpleNamespace(bot_active=True)
    access = await _resolver("free").resolve_adv_ui_access(373435337, adv)
    assert access == UiAccessMode.FREE


@pytest.mark.asyncio
async def test_adv_resolver_admin_paid_override() -> None:
    adv = SimpleNamespace(bot_active=False)
    access = await _resolver("paid").resolve_adv_ui_access(373435337, adv)
    assert access == UiAccessMode.PAID
