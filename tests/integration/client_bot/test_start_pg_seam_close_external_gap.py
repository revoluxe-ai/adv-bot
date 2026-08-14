"""Integration coverage for start.py PG seam helpers.

These tests exercise the child `*_in_session` helpers with a live
`async_session` and re-read persisted state from PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload

import app.client_bot.user_interface.handlers.start.start as start_module
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _make_user(
    async_session,
    *,
    telegram_id: int,
    username: str,
) -> User:
    """Create a persisted Telegram user for seam tests."""
    user = User(
        user_telegram_id=telegram_id,
        username=username,
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    return user


async def _make_cabinet(
    async_session,
    *,
    shop_id: str,
    active: bool = True,
) -> WBCabinet:
    """Create a persisted WB cabinet with deterministic defaults."""
    cabinet = WBCabinet(
        shop_id=shop_id,
        active=active,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()
    return cabinet


async def _make_user_cabinet(
    async_session,
    *,
    user: User,
    cabinet: WBCabinet,
    name: str,
) -> WBUserCabinet:
    """Attach an existing cabinet to a user."""
    user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name=name,
    )
    async_session.add(user_cabinet)
    await async_session.flush()
    return user_cabinet


async def _make_adv_setting(
    async_session,
    *,
    cabinet: WBCabinet,
    name: str,
    adv_id: int,
) -> AdvSetting:
    """Create an AdvSetting row linked to the given cabinet."""
    adv_setting = AdvSetting(
        adv_id=adv_id,
        name=name,
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
    )
    async_session.add(adv_setting)
    await async_session.flush()
    return adv_setting


async def _make_token(
    async_session,
    *,
    user: User,
    shop_id: str,
    api_key: str,
) -> WBToken:
    """Create a token row bound to the user and shop."""
    token = WBToken(api_key=api_key, user_id=user.id, shop_id=shop_id)
    async_session.add(token)
    await async_session.flush()
    return token


async def test_load_user_with_wb_cabinets_in_session_reads_persisted_relations(
    async_session,
) -> None:
    """Child loader returns the user with re-readable cabinets."""
    telegram_id = 9_100_101
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="start-user-cabinets"
    )
    cabinet_one = await _make_cabinet(
        async_session, shop_id=f"shop-{uuid.uuid4().hex[:8]}", active=True
    )
    cabinet_two = await _make_cabinet(
        async_session, shop_id=f"shop-{uuid.uuid4().hex[:8]}", active=True
    )
    await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet_one, name="Cabinet A"
    )
    await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet_two, name="Cabinet B"
    )

    loaded = await start_module._load_user_with_wb_cabinets_in_session(
        async_session, telegram_id
    )
    assert loaded is not None
    assert sorted(
        user_cabinet.wb_cabinet.shop_id for user_cabinet in loaded.wb_user_cabinets
    ) == sorted([cabinet_one.shop_id, cabinet_two.shop_id])

    async_session.expire_all()
    reread = await async_session.execute(
        select(User)
        .options(joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet))
        .where(User.user_telegram_id == telegram_id)
    )
    reread_user = reread.unique().scalar_one()
    assert len(reread_user.wb_user_cabinets) == 2


async def test_load_user_id_in_session_reads_persisted_pk(async_session) -> None:
    """Child loader returns the same user PK that PostgreSQL stores."""
    telegram_id = 9_100_102
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="start-user-id"
    )
    user_pk = user.id

    loaded_id = await start_module._load_user_id_in_session(async_session, telegram_id)
    assert loaded_id == user_pk

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread_id = await async_session.scalar(
        select(User.id).where(User.user_telegram_id == telegram_id)
    )
    assert reread_id == user_pk


async def test_load_wb_user_cabinet_in_session_reads_persisted_cabinet(
    async_session,
) -> None:
    """Child loader returns the cabinet row and its related WB cabinet."""
    telegram_id = 9_100_103
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="start-user-cabinet"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    cabinet = await _make_cabinet(async_session, shop_id=shop_id, active=True)
    user_cabinet = await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet, name="Cabinet C"
    )
    user_cabinet_pk = user_cabinet.id

    loaded = await start_module._load_wb_user_cabinet_in_session(
        async_session, user_cabinet_pk
    )
    assert loaded is not None
    assert loaded.wb_cabinet.shop_id == shop_id
    assert loaded.name == "Cabinet C"

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread_name = await async_session.scalar(
        select(WBUserCabinet.name).where(WBUserCabinet.id == user_cabinet_pk)
    )
    assert reread_name == "Cabinet C"


async def test_load_wb_user_cabinet_for_owner_in_session_filters_by_telegram_id(
    async_session,
) -> None:
    """Owner loader returns cabinet only when telegram_id matches persisted User."""
    owner_telegram_id = 9_100_203
    other_telegram_id = 9_100_204
    owner = await _make_user(
        async_session, telegram_id=owner_telegram_id, username="start-owner-ok"
    )
    await _make_user(
        async_session, telegram_id=other_telegram_id, username="start-owner-other"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    cabinet = await _make_cabinet(async_session, shop_id=shop_id, active=True)
    user_cabinet = await _make_user_cabinet(
        async_session, user=owner, cabinet=cabinet, name="Owner Cabinet"
    )
    user_cabinet_pk = user_cabinet.id
    await async_session.commit()

    loaded = await start_module._load_wb_user_cabinet_for_owner_in_session(
        async_session, user_cabinet_pk, owner_telegram_id
    )
    assert loaded is not None
    assert loaded.id == user_cabinet_pk
    assert loaded.name == "Owner Cabinet"
    assert loaded.wb_cabinet.shop_id == shop_id

    denied = await start_module._load_wb_user_cabinet_for_owner_in_session(
        async_session, user_cabinet_pk, other_telegram_id
    )
    assert denied is None

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread_name = await async_session.scalar(
        select(WBUserCabinet.name).where(WBUserCabinet.id == user_cabinet_pk)
    )
    assert reread_name == "Owner Cabinet"


async def test_load_adv_settings_for_wb_user_cabinet_in_session_reads_ordered_rows(
    async_session,
) -> None:
    """Child loader returns AdvSettings ordered by name from PostgreSQL."""
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    cabinet = await _make_cabinet(async_session, shop_id=shop_id, active=True)
    cabinet_pk = cabinet.id
    await _make_adv_setting(async_session, cabinet=cabinet, name="beta", adv_id=2)
    await _make_adv_setting(async_session, cabinet=cabinet, name="alpha", adv_id=1)
    user = await _make_user(
        async_session, telegram_id=9_100_104, username="start-adv-user"
    )
    user_cabinet = await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet, name="Cabinet D"
    )
    user_cabinet_pk = user_cabinet.id

    loaded = await start_module._load_adv_settings_for_wb_user_cabinet_in_session(
        async_session, user_cabinet_pk
    )
    assert [adv.name for adv in loaded] == ["alpha", "beta"]

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread_names = await async_session.scalars(
        select(AdvSetting.name)
        .where(AdvSetting.wb_cabinet_id == cabinet_pk)
        .order_by(AdvSetting.name)
    )
    assert list(reread_names) == ["alpha", "beta"]


async def test_load_wb_user_cabinet_for_menu_in_session_reads_user_tokens_and_settings(
    async_session,
) -> None:
    """Menu helper eager-loads user tokens and cabinet adv settings."""
    telegram_id = 9_100_105
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="start-menu-user"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    cabinet = await _make_cabinet(async_session, shop_id=shop_id, active=True)
    token = await _make_token(
        async_session,
        user=user,
        shop_id=shop_id,
        api_key=f"token-{uuid.uuid4().hex}",
    )
    token_api_key = token.api_key
    adv_setting = await _make_adv_setting(
        async_session, cabinet=cabinet, name="menu-adv", adv_id=11
    )
    adv_setting_name = adv_setting.name
    user_cabinet = await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet, name="Cabinet Menu"
    )
    user_cabinet_pk = user_cabinet.id

    loaded = await start_module._load_wb_user_cabinet_for_menu_in_session(
        async_session, user_cabinet_pk
    )
    assert loaded is not None
    assert loaded.user.user_telegram_id == telegram_id
    assert loaded.user.wb_tokens[0].api_key == token_api_key
    assert loaded.wb_cabinet.adv_settings[0].name == adv_setting_name

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread = await async_session.execute(
        select(WBUserCabinet)
        .options(
            joinedload(WBUserCabinet.user).joinedload(User.wb_tokens),
            joinedload(WBUserCabinet.wb_cabinet).joinedload(WBCabinet.adv_settings),
        )
        .where(WBUserCabinet.id == user_cabinet_pk)
    )
    reread_user_cabinet = reread.unique().scalar_one()
    assert reread_user_cabinet.user.wb_tokens[0].api_key == token_api_key
    assert reread_user_cabinet.wb_cabinet.adv_settings[0].name == adv_setting_name


@pytest.mark.asyncio
async def test_persist_wb_token_in_session_persists(async_session) -> None:
    """WRITE child persists WBToken; re-select proves row."""
    user = await _make_user(
        async_session, telegram_id=9_100_201, username="persist-token-user"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    api_key = f"api-{uuid.uuid4().hex}"
    token = WBToken(api_key=api_key, user_id=user.id, shop_id=shop_id, active=True)

    await start_module.persist_wb_token_in_session(async_session, token)
    async_session.expire_all()
    reread = await async_session.scalar(
        select(WBToken).where(WBToken.api_key == api_key, WBToken.shop_id == shop_id)
    )
    assert reread is not None
    assert reread.user_id == user.id


@pytest.mark.asyncio
async def test_create_wb_cabinet_and_user_binding_in_session_persists(
    async_session,
) -> None:
    """WRITE child creates cabinet + binding; re-select proves both."""
    user = await _make_user(
        async_session, telegram_id=9_100_202, username="create-cab-user"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"

    cabinet, user_cabinet = (
        await start_module.create_wb_cabinet_and_user_binding_in_session(
            async_session,
            shop_id=shop_id,
            user_id=user.id,
            cabinet_name="New Cabinet",
        )
    )
    async_session.expire_all()
    reread_cab = await async_session.scalar(
        select(WBCabinet).where(WBCabinet.id == cabinet.id)
    )
    reread_uc = await async_session.scalar(
        select(WBUserCabinet).where(WBUserCabinet.id == user_cabinet.id)
    )
    assert reread_cab is not None
    assert reread_cab.shop_id == shop_id
    assert reread_cab.active is True
    assert reread_uc is not None
    assert reread_uc.user_id == user.id
    assert reread_uc.name == "New Cabinet"


@pytest.mark.asyncio
async def test_ensure_wb_user_cabinet_binding_in_session_creates(
    async_session,
) -> None:
    """WRITE child creates missing binding; re-select proves row."""
    user = await _make_user(
        async_session, telegram_id=9_100_203, username="ensure-bind-user"
    )
    cabinet = await _make_cabinet(
        async_session, shop_id=f"shop-{uuid.uuid4().hex[:8]}", active=True
    )
    await async_session.commit()

    binding = await start_module.ensure_wb_user_cabinet_binding_in_session(
        async_session,
        wb_cabinet=cabinet,
        user_id=user.id,
        cabinet_name="Bound Cabinet",
    )
    async_session.expire_all()
    reread = await async_session.scalar(
        select(WBUserCabinet).where(WBUserCabinet.id == binding.id)
    )
    assert reread is not None
    assert reread.wb_cabinet_id == cabinet.id
    assert reread.user_id == user.id


@pytest.mark.asyncio
async def test_commit_new_wb_token_in_session_persists(async_session) -> None:
    """WRITE child for process_add_new_token persists token."""
    user = await _make_user(
        async_session, telegram_id=9_100_204, username="commit-token-user"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    api_key = f"api-{uuid.uuid4().hex}"
    token = WBToken(api_key=api_key, user_id=user.id, shop_id=shop_id, active=True)

    await start_module.commit_new_wb_token_in_session(async_session, token)
    async_session.expire_all()
    reread = await async_session.scalar(
        select(WBToken).where(WBToken.api_key == api_key, WBToken.shop_id == shop_id)
    )
    assert reread is not None
    assert reread.user_id == user.id


@pytest.mark.asyncio
async def test_process_cabinet_api_parent_live_sm_creates_cabinet_and_token(
    async_session,
) -> None:
    """Parent ``process_cabinet_api`` persists token+cabinet via live sm.

    Non-PG deps (token validator, Telegram messages, ShopChoice) are mocked
    after the causal PG boundary. ``sm`` is already live via package conftest.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    telegram_id = 9_100_301
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="cabinet-api-parent"
    )
    await async_session.commit()
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    api_key = f"tok-{uuid.uuid4().hex}abcdef"  # >= 24 chars

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
        text=api_key,
        chat=SimpleNamespace(id=telegram_id),
        from_user=SimpleNamespace(id=telegram_id),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"cabinet_name": "Live Cab"})
    client_session = MagicMock()

    with (
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module.messages,
            "ShopUpdateInfo",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(
            start_module.messages,
            "ShopAddedSuccess",
            MagicMock(return_value=AsyncMock()),
        ),
        patch.object(
            start_module,
            "ShopChoice",
            MagicMock(return_value=AsyncMock()),
        ),
    ):
        await start_module.process_cabinet_api(
            message, bot, state, client_session
        )

    async_session.expire_all()
    reread_token = await async_session.scalar(
        select(WBToken).where(WBToken.api_key == api_key, WBToken.shop_id == shop_id)
    )
    reread_cab = await async_session.scalar(
        select(WBCabinet).where(WBCabinet.shop_id == shop_id)
    )
    reread_uc = await async_session.scalar(
        select(WBUserCabinet).where(
            WBUserCabinet.user_id == user.id,
            WBUserCabinet.name == "Live Cab",
        )
    )
    assert reread_token is not None
    assert reread_token.user_id == user.id
    assert reread_cab is not None
    assert reread_cab.active is True
    assert reread_uc is not None
    assert reread_uc.wb_cabinet_id == reread_cab.id


@pytest.mark.asyncio
async def test_process_add_new_token_parent_live_sm_persists_token(
    async_session,
) -> None:
    """Parent ``process_add_new_token`` persists WBToken via live write sm."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    telegram_id = 9_100_302
    user = await _make_user(
        async_session, telegram_id=telegram_id, username="add-token-parent"
    )
    shop_id = f"shop-{uuid.uuid4().hex[:8]}"
    cabinet = await _make_cabinet(async_session, shop_id=shop_id, active=True)
    user_cabinet = await _make_user_cabinet(
        async_session, user=user, cabinet=cabinet, name="Existing Cab"
    )
    await async_session.commit()
    api_key = f"tok-{uuid.uuid4().hex}abcdef"

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
        text=api_key,
        chat=SimpleNamespace(id=telegram_id),
        from_user=SimpleNamespace(id=telegram_id),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={"wb_user_cabinet_original_id": user_cabinet.id}
    )
    state.clear = AsyncMock()
    client_session = MagicMock()

    with (
        patch.object(
            start_module,
            "TokenPermissionsValidator",
            MagicMock(return_value=validator),
        ),
        patch.object(
            start_module,
            "NotificationManager",
            MagicMock(return_value=notif),
        ),
        patch.object(
            start_module,
            "ShopMenu",
            MagicMock(return_value=AsyncMock()),
        ),
    ):
        await start_module.process_add_new_token(
            message, bot, state, client_session
        )

    async_session.expire_all()
    reread = await async_session.scalar(
        select(WBToken).where(WBToken.api_key == api_key, WBToken.shop_id == shop_id)
    )
    assert reread is not None
    assert reread.user_id == user.id
    state.clear.assert_awaited()
