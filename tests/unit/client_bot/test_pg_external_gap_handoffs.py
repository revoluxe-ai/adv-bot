"""Mock-only regression coverage for the newly injectable PG handoff helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers.adv_setting import adv_setting
from app.client_bot.user_interface.handlers import keyword_settings
from app.client_bot.user_interface.views.messages import messages as message_views
from app.client_bot.user_interface.views.messages.messages import AdvCompanyChoicing
from app.modules.adv_creator.backend.main_manager import MainAdvManager
from app.modules.billing import billing
from app.modules.shop_runner.service_manager import manager
from app.modules.shop_runner.service_manager.auto_updater_version_toggle.telegram import (
    handlers as auto_updater_handlers,
)
from app.modules.shop_runner.service_manager.services import (
    auto_updater_version_migration,
)
from app.modules.white_list_mode_settings.telegram.main_message import (
    WhiteListModeMenuMessage,
)


def _session_with_result(result: object) -> MagicMock:
    """Создать минимальную fake-сессию, сохраняющую реальный вызов execute."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.scalars = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_adv_setting_loader_uses_parent_session() -> None:
    """Campaign loader must execute SQL through the injected PG session."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = [SimpleNamespace(id=1)]
    session = _session_with_result(result)

    loaded = await adv_setting._load_adv_settings_for_cabinet(session, 10)

    assert loaded == [SimpleNamespace(id=1)]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_adv_setting_single_loader_uses_parent_session() -> None:
    """Single campaign lookup must use the injected PG session."""
    campaign = SimpleNamespace(id=1)
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    session = _session_with_result(result)

    loaded = await adv_setting._load_adv_setting_in_session(session, 1)

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_keyword_setting_loader_uses_parent_session() -> None:
    """Keyword UI loader must use the session handed off by its parent."""
    campaign = SimpleNamespace(id=11)
    result = MagicMock()
    result.scalar.return_value = campaign
    session = _session_with_result(result)

    loaded = await keyword_settings._load_adv_setting(session, 11)

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_keyword_setting_with_cabinet_loader_uses_parent_session() -> None:
    """Keyword screen campaign loader must use the handed-off session."""
    campaign = SimpleNamespace(id=11)
    result = MagicMock()
    result.scalar_one.return_value = campaign
    session = _session_with_result(result)

    loaded = await keyword_settings._load_adv_setting_with_cabinet_in_session(
        session, 11
    )

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_adv_manager_loader_uses_parent_session() -> None:
    """Adv ID lookup must execute against the injected read-only session."""
    result = MagicMock()
    result.all.return_value = [(101,), (102,)]
    session = _session_with_result(result)

    loaded = await MainAdvManager._get_all_adv_ids_for_nmid_in_session(
        session, 7, 42
    )

    assert loaded == {101, 102}
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_adv_ids_by_nmid_loader_uses_parent_session() -> None:
    """Nmid campaign lookup must execute against the injected session."""
    result = MagicMock()
    result.all.return_value = [
        SimpleNamespace(adv_id=101, search_adv_id=201),
        SimpleNamespace(adv_id=102, search_adv_id=None),
    ]
    session = _session_with_result(result)

    loaded = await MainAdvManager._get_adv_ids_rows_by_nmid_in_session(session, 7)

    assert loaded == [(101, 201)]
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_billing_loader_uses_parent_session() -> None:
    """Billing notifications must load recipients through the injected session."""
    result = MagicMock()
    result.all.return_value = [(1, 1001), (2, None)]
    session = _session_with_result(result)

    loaded = await billing._load_cabinet_user_chats(session, 7)

    assert loaded == [(1, 1001), (2, None)]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_cabinet_loader_uses_parent_session() -> None:
    """Campaign menu cabinet lookup must use the handed-off session."""
    cabinet = SimpleNamespace(id=7)
    result = MagicMock()
    result.scalar.return_value = cabinet
    session = _session_with_result(result)

    loaded = await AdvCompanyChoicing._get_wb_cabinet_in_session(session, 7)

    assert loaded is cabinet
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_cabinet_id_loader_uses_parent_session() -> None:
    """Message cabinet ID lookup must use the handed-off session."""
    result = MagicMock()
    result.scalar.return_value = 7
    session = _session_with_result(result)

    loaded = await message_views._load_wb_cabinet_id_for_user_cabinet(session, 8)

    assert loaded == 7
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_adv_loader_uses_parent_session() -> None:
    """Message campaign lookup must execute through the injected session."""
    campaign = SimpleNamespace(id=7)
    result = MagicMock()
    result.scalar.return_value = campaign
    session = _session_with_result(result)

    loaded = await message_views._load_adv_setting_in_session(session, 7)

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_updater_menu_loader_uses_parent_session() -> None:
    """AutoUpdater menu lookup must execute through the injected session."""
    campaign = SimpleNamespace(id=7)
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    session = _session_with_result(result)

    loaded = await auto_updater_handlers._load_adv_for_version_menu(session, 7)

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_updater_toggle_loader_uses_parent_session() -> None:
    """Version toggle lookup must execute through the WRITE session seam."""
    campaign = SimpleNamespace(id=7)
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    session = _session_with_result(result)

    loaded = await auto_updater_handlers._load_adv_for_toggle_in_session(session, 7)

    assert loaded is campaign
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_strategy_updates_use_parent_session() -> None:
    """Strategy writes must run and commit through the handed-off session."""
    result = SimpleNamespace(rowcount=1)
    session = _session_with_result(result)
    service = manager.CoroutinesManager.__new__(manager.CoroutinesManager)
    service.shop_id = "shop-1"

    await service._apply_strategy_updates_in_session(
        session,
        [(1, 2, "old", "new", "test")],
    )

    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_updater_migration_uses_parent_session() -> None:
    """AutoUpdater migration must execute and commit in the injected session."""
    result = SimpleNamespace(rowcount=2)
    session = _session_with_result(result)

    migrated = await auto_updater_version_migration._migrate_v1_auto_updaters_in_session(
        session, [1, 2]
    )

    assert migrated == 2
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_white_list_loader_uses_parent_session() -> None:
    """White-list menu lookup must execute through the handed-off session."""
    campaign = SimpleNamespace(adv_id=7)
    result = MagicMock()
    result.scalar_one.return_value = campaign
    session = _session_with_result(result)

    loaded = await WhiteListModeMenuMessage._get_adv_in_session(session, 7)

    assert loaded is campaign
    session.execute.assert_awaited_once()
