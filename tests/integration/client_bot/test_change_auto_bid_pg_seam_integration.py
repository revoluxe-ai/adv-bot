"""Integration coverage for PG seam in change_auto_bid handlers.

Проверяет, что выделенные child-функции работают через живой ``async_session``
и подтверждают persisted состояние повторным чтением из БД.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers import change_auto_bid
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_adv_setting(async_session: AsyncSession) -> AdvSetting:
    """Создать минимальный AdvSetting для интеграционных тестов PG seam."""
    cabinet = WBCabinet(
        shop_id=f"change_auto_bid_test_{uuid.uuid4().hex}",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()

    adv_setting = AdvSetting(
        adv_id=123_777,
        name="change-auto-bid-test",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=75,
    )
    async_session.add(adv_setting)
    await async_session.flush()
    return adv_setting


async def _create_user_cabinet_for_adv(
    async_session: AsyncSession,
    adv_setting: AdvSetting,
    *,
    telegram_id: int,
) -> WBUserCabinet:
    """Создать User + WBUserCabinet, привязанные к кабинету AdvSetting."""
    user = User(
        user_telegram_id=telegram_id,
        username=f"change_auto_bid_tg_{telegram_id}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=adv_setting.wb_cabinet_id,
        name="change-auto-bid-user-cabinet",
    )
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    return wb_user_cabinet


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_adv_setting_with_cabinet_reads_via_injected_session(
    async_session: AsyncSession,
) -> None:
    """`_load_adv_setting_with_cabinet` читает AdvSetting через переданную session."""
    adv_setting = await _create_adv_setting(async_session)

    loaded = await change_auto_bid._load_adv_setting_with_cabinet(  # noqa: SLF001
        async_session,
        adv_setting.id,
    )

    assert loaded is not None
    assert loaded.id == adv_setting.id
    assert loaded.wb_cabinet is not None
    assert loaded.wb_cabinet.id == adv_setting.wb_cabinet_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_adv_setting_for_menu_reads_via_injected_session(
    async_session: AsyncSession,
) -> None:
    """`_load_adv_setting_for_menu` PURE_READ: injected session + SQL re-read."""
    adv_setting = await _create_adv_setting(async_session)

    loaded = await change_auto_bid._load_adv_setting_for_menu(  # noqa: SLF001
        async_session,
        adv_setting.id,
    )

    assert loaded is not None
    assert loaded.id == adv_setting.id
    assert loaded.cpm == adv_setting.cpm

    reread_id = await async_session.scalar(
        select(AdvSetting.id).where(AdvSetting.id == adv_setting.id)
    )
    reread_cpm = await async_session.scalar(
        select(AdvSetting.cpm).where(AdvSetting.id == adv_setting.id)
    )
    assert reread_id == loaded.id
    assert int(reread_cpm or 0) == int(loaded.cpm or 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_wb_user_cabinet_for_adv_and_telegram_reads_via_injected_session(
    async_session: AsyncSession,
) -> None:
    """`_get_wb_user_cabinet_for_adv_and_telegram` PURE_READ + SQL re-read."""
    telegram_id = 9_101_202_607
    adv_setting = await _create_adv_setting(async_session)
    expected = await _create_user_cabinet_for_adv(
        async_session,
        adv_setting,
        telegram_id=telegram_id,
    )

    loaded = await change_auto_bid._get_wb_user_cabinet_for_adv_and_telegram(  # noqa: SLF001
        async_session,
        adv_setting,
        telegram_id,
    )

    assert loaded is not None
    assert loaded.id == expected.id
    assert loaded.wb_cabinet_id == adv_setting.wb_cabinet_id
    assert loaded.user_id == expected.user_id

    reread = await async_session.scalar(
        select(WBUserCabinet)
        .join(User, User.id == WBUserCabinet.user_id)
        .where(User.user_telegram_id == telegram_id)
        .where(WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id)
    )
    assert reread is not None
    assert reread.id == loaded.id
    assert reread.user_id == loaded.user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persist_adv_cpm_writes_and_is_visible_on_reread(
    async_session: AsyncSession,
) -> None:
    """`_persist_adv_cpm` обновляет cpm и изменение видно при re-read из БД."""
    adv_setting = await _create_adv_setting(async_session)
    new_cpm = 133

    updated = await change_auto_bid._persist_adv_cpm(  # noqa: SLF001
        async_session,
        adv_setting.id,
        new_cpm,
    )

    assert updated is True
    reread = await async_session.scalar(
        select(AdvSetting.cpm).where(AdvSetting.id == adv_setting.id)
    )
    assert int(reread or 0) == new_cpm
