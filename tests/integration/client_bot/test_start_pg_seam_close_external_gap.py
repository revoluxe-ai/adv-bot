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
