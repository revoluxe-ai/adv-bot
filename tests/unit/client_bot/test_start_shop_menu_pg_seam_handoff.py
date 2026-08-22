"""Mock-only handoff proofs for start WRITE children and ShopMenu tariff seam."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.client_bot.user_interface.handlers.start.start as start_module
import app.modules.shop_menu.message as shop_menu_mod

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _SessionMakerMock:
    """Async context manager returned by a fake ``sm`` callable."""

    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def _session_cm(session: AsyncSession):
    """Build session-maker double that records explicit ``read_only=``."""

    @asynccontextmanager
    async def cm(*, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        cm.last_read_only = read_only  # type: ignore[attr-defined]
        yield session

    cm.last_read_only = None  # type: ignore[attr-defined]
    return cm


@pytest.mark.asyncio
async def test_persist_wb_token_in_session_adds_and_commits() -> None:
    """WRITE child adds token then flush+commit on injected session."""
    session = AsyncMock(spec=AsyncSession)
    token = SimpleNamespace(api_key="k", user_id=1, shop_id="s")

    await start_module.persist_wb_token_in_session(session, token)  # type: ignore[arg-type]

    session.add.assert_called_once_with(token)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_new_wb_token_in_session_adds_and_commits() -> None:
    """WRITE child for add-new-token adds then commits."""
    session = AsyncMock(spec=AsyncSession)
    token = SimpleNamespace(api_key="k2", user_id=2, shop_id="s2")

    await start_module.commit_new_wb_token_in_session(session, token)  # type: ignore[arg-type]

    session.add.assert_called_once_with(token)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_wb_cabinet_and_user_binding_hands_session_ops() -> None:
    """WRITE child creates cabinet + binding on injected session."""
    session = AsyncMock(spec=AsyncSession)

    async def _flush() -> None:
        for call in session.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None and hasattr(obj, "shop_id"):
                obj.id = 77

    session.flush = AsyncMock(side_effect=_flush)

    with patch.object(start_module, "settings", SimpleNamespace(DEFAULT_MAX_CPM=350)):
        cabinet, user_cabinet = (
            await start_module.create_wb_cabinet_and_user_binding_in_session(
                session,
                shop_id="shop-x",
                user_id=9,
                cabinet_name="Cab",
            )
        )

    assert cabinet.shop_id == "shop-x"
    assert cabinet.active is True
    assert cabinet.default_max_cpm == 350
    assert user_cabinet.user_id == 9
    assert user_cabinet.wb_cabinet_id == 77
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_shop_menu_tariff_block_hands_read_session_to_child() -> None:
    """``_load_all_data`` tariff block opens ``sm(read_only=True)`` → child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    menu = MagicMock()
    menu._wb_cabinet = SimpleNamespace(shop_id="shop-tariff")
    menu._pricer = MagicMock()
    child = AsyncMock(return_value=SimpleNamespace(count=3))
    menu._load_tariff_details_in_session = child

    with patch.object(shop_menu_mod, "sm", sm_cm):
        async with shop_menu_mod.sm(read_only=True) as sess:
            details = await menu._load_tariff_details_in_session(sess, "shop-tariff")

    assert sm_cm.last_read_only is True
    child.assert_awaited_once_with(session, "shop-tariff")
    assert details.count == 3


@pytest.mark.asyncio
async def test_load_tariff_details_in_session_delegates_to_pricer() -> None:
    """ShopMenu tariff child delegates to Pricer on injected session."""
    session = AsyncMock(spec=AsyncSession)
    menu = object.__new__(shop_menu_mod.ShopMenu)
    menu._pricer = MagicMock()
    menu._pricer.get_tariff_details = AsyncMock(
        return_value=SimpleNamespace(count=0)
    )

    details = await shop_menu_mod.ShopMenu._load_tariff_details_in_session(
        menu, session, "shop-1"
    )

    menu._pricer.get_tariff_details.assert_awaited_once_with(session, "shop-1")
    assert details.count == 0


@pytest.mark.asyncio
async def test_process_cabinet_api_new_shop_hands_write_session_to_persist_children() -> None:
    """Parent new-shop path opens write sm and calls WRITE children."""
    session = MagicMock(name="cabinet_api_new_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    user_id_loader = AsyncMock(return_value=42)
    existing_token_loader = AsyncMock(return_value=None)
    persist_token = AsyncMock()
    load_cabinet = AsyncMock(return_value=None)
    create_binding = AsyncMock(
        return_value=(
            SimpleNamespace(id=1, shop_id="shop-new"),
            SimpleNamespace(id=2, name="Cab"),
        )
    )
    load_user_cabinets = AsyncMock(return_value=[])
    shop_id = "shop-new"
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)

    message = SimpleNamespace(
        text="y" * 32,
        chat=SimpleNamespace(id=111),
        from_user=SimpleNamespace(id=222),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Cab"})
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(
            start_module, "_load_existing_wb_token_in_session", existing_token_loader
        ),
        patch.object(start_module, "persist_wb_token_in_session", persist_token),
        patch.object(
            start_module, "_load_wb_cabinet_by_shop_id_in_session", load_cabinet
        ),
        patch.object(
            start_module,
            "create_wb_cabinet_and_user_binding_in_session",
            create_binding,
        ),
        patch.object(
            start_module, "_load_user_cabinets_for_user_in_session", load_user_cabinets
        ),
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module.messages, "ShopUpdateInfo", MagicMock(return_value=AsyncMock())
        ),
        patch.object(
            start_module.messages,
            "ShopAddedSuccess",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(start_module, "ShopChoice", MagicMock(return_value=AsyncMock())),
    ):
        await start_module.process_cabinet_api(message, bot, state, client_session)

    persist_token.assert_awaited_once()
    create_binding.assert_awaited_once()
    assert create_binding.await_args.kwargs["shop_id"] == shop_id
    assert create_binding.await_args.kwargs["user_id"] == 42


@pytest.mark.asyncio
async def test_process_add_new_token_hands_write_session_to_commit_child() -> None:
    """Parent add-token path opens write sm and commits via child."""
    session = MagicMock(name="add_token_write_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    shop_id = "shop-add"
    user_id_loader = AsyncMock(return_value=7)
    cabinet = SimpleNamespace(
        id=9,
        name="Cab",
        wb_cabinet=SimpleNamespace(shop_id=shop_id, active=True),
    )
    load_uc = AsyncMock(return_value=cabinet)
    load_existing = AsyncMock(return_value=None)
    commit_token = AsyncMock()
    load_cab = AsyncMock(return_value=cabinet.wb_cabinet)
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)
    notif = MagicMock()
    notif.mark_notifications_resolved = AsyncMock(return_value=0)

    message = SimpleNamespace(
        text="z" * 32,
        chat=SimpleNamespace(id=333),
        from_user=SimpleNamespace(id=444),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 9})
    state.clear = AsyncMock()
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(start_module, "_load_wb_user_cabinet_in_session", load_uc),
        patch.object(
            start_module, "_load_existing_wb_token_in_session", load_existing
        ),
        patch.object(start_module, "commit_new_wb_token_in_session", commit_token),
        patch.object(
            start_module, "_load_wb_cabinet_by_shop_id_in_session", load_cab
        ),
        patch.object(
            start_module, "TokenPermissionsValidator", MagicMock(return_value=validator)
        ),
        patch.object(
            start_module, "NotificationManager", MagicMock(return_value=notif)
        ),
        patch.object(start_module, "ShopMenu", MagicMock(return_value=AsyncMock())),
    ):
        await start_module.process_add_new_token(message, bot, state, client_session)

    commit_token.assert_awaited_once()
    assert commit_token.await_args.args[0] is session
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_add_new_token_strips_whitespace_before_validate_and_persist() -> None:
    """Surrounding whitespace must not reach validator or WBToken.api_key."""
    session = MagicMock(name="add_token_strip_session")
    sm_mock = MagicMock(return_value=_SessionMakerMock(session))
    raw_token = "t" * 32
    shop_id = "shop-strip"
    user_id_loader = AsyncMock(return_value=7)
    cabinet = SimpleNamespace(
        id=9,
        name="Cab",
        wb_cabinet=SimpleNamespace(shop_id=shop_id, active=True),
    )
    load_uc = AsyncMock(return_value=cabinet)
    load_existing = AsyncMock(return_value=None)
    commit_token = AsyncMock()
    load_cab = AsyncMock(return_value=cabinet.wb_cabinet)
    validation_result = SimpleNamespace(
        is_valid_jwt=True,
        is_personal=True,
        is_read_only=False,
        is_expired=False,
        can_be_used_for_free=True,
        missing_required=set(),
        shop_id=shop_id,
    )
    validator = MagicMock()
    validator.validate = AsyncMock(return_value=validation_result)
    notif = MagicMock()
    notif.mark_notifications_resolved = AsyncMock(return_value=0)

    message = SimpleNamespace(
        text=f"  {raw_token}  ",
        chat=SimpleNamespace(id=333),
        from_user=SimpleNamespace(id=444),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 9})
    state.clear = AsyncMock()
    client_session = MagicMock()

    with (
        patch.object(start_module, "sm", sm_mock),
        patch.object(start_module, "_load_user_id_in_session", user_id_loader),
        patch.object(start_module, "_load_wb_user_cabinet_in_session", load_uc),
        patch.object(
            start_module, "_load_existing_wb_token_in_session", load_existing
        ),
        patch.object(start_module, "commit_new_wb_token_in_session", commit_token),
        patch.object(
            start_module, "_load_wb_cabinet_by_shop_id_in_session", load_cab
        ),
        patch.object(
            start_module, "TokenPermissionsValidator", MagicMock(return_value=validator)
        ),
        patch.object(
            start_module, "NotificationManager", MagicMock(return_value=notif)
        ),
        patch.object(start_module, "ShopMenu", MagicMock(return_value=AsyncMock())),
    ):
        await start_module.process_add_new_token(message, bot, state, client_session)

    validator.validate.assert_awaited_once_with(raw_token, mode="claims_plus_api")
    saved_token = commit_token.await_args.args[1]
    assert saved_token.api_key == raw_token
