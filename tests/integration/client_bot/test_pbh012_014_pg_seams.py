"""Integration coverage for PBH-012/013/014 PG seams (black / relevant / toggle).

Проверяет injectable ``*_in_session`` через живой ``async_session`` + SQL
re-read. Не marker ``fast``; live DB via fixture. Authored for
``/opsx-close-external-gap`` — не запускать без ``AUTHORIZE_ONE_LIVE_RUN``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers import (
    add_black_phrases,
    add_relevant_phrase_templates,
    auto_add_only_relevant_phrase_toggle,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Минимальный WBCabinet для seam-тестов PBH-012/013/014."""
    cabinet = WBCabinet(
        shop_id=f"pbh_seam_{uuid.uuid4().hex}",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()
    return cabinet


async def _create_adv(
    async_session: AsyncSession,
    *,
    cabinet: WBCabinet,
    hold_mode: str | None = None,
    auto_add_only_relevant_phrase: bool = False,
) -> AdvSetting:
    """Минимальный AdvSetting с опциональным A/B Hold mode."""
    adv = AdvSetting(
        adv_id=int(uuid.uuid4().int % 1_000_000) + 60_000,
        name="pbh-012-014-seam-test",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        card_ab_hold_mode=hold_mode,
        auto_add_only_relevant_phrase=auto_add_only_relevant_phrase,
        black_phrases=["old-black"],
        relevant_phrases=["old-rel"],
    )
    async_session.add(adv)
    await async_session.flush()
    return adv


@pytest.mark.integration
@pytest.mark.asyncio
async def test_black_load_adv_setting_in_session_reads_mode(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child (black): ``load_adv_setting_in_session`` + re-select."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    await async_session.commit()

    loaded = await add_black_phrases.load_adv_setting_in_session(
        async_session, adv.id
    )
    assert loaded is not None
    assert loaded.id == adv.id
    assert loaded.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value

    reread = await async_session.scalar(
        select(AdvSetting.card_ab_hold_mode).where(AdvSetting.id == adv.id)
    )
    assert reread == CardAbHoldMode.ACTIVE.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relevant_load_adv_setting_in_session_reads_mode(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child (relevant templates): ``load_adv_setting_in_session`` + re-select."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.PENDING_SETUP.value,
    )
    await async_session.commit()

    loaded = await add_relevant_phrase_templates.load_adv_setting_in_session(
        async_session, adv.id
    )
    assert loaded is not None
    assert loaded.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value

    reread = await async_session.scalar(
        select(AdvSetting.card_ab_hold_mode).where(AdvSetting.id == adv.id)
    )
    assert reread == CardAbHoldMode.PENDING_SETUP.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toggle_load_adv_setting_by_pk_in_session_reads_mode(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child (toggle menu): ``load_adv_setting_by_pk_in_session`` + re-select.

    Parent ``open_relevant_phrase_management_menu`` передаёт PK ``AdvSetting.id``
    (не ``adv_id``) в ``sm(read_only=True)`` scope. Coverage закрывает WEAK_EVIDENCE
    для PG-seam load-by-pk.
    """
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
        auto_add_only_relevant_phrase=True,
    )
    await async_session.commit()
    adv_pk = adv.id

    loaded = await (
        auto_add_only_relevant_phrase_toggle.load_adv_setting_by_pk_in_session(
            async_session, adv_pk
        )
    )
    assert loaded is not None
    assert loaded.id == adv_pk
    assert loaded.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    assert loaded.auto_add_only_relevant_phrase is True

    reread_mode = await async_session.scalar(
        select(AdvSetting.card_ab_hold_mode).where(AdvSetting.id == adv_pk)
    )
    reread_flag = await async_session.scalar(
        select(AdvSetting.auto_add_only_relevant_phrase).where(
            AdvSetting.id == adv_pk
        )
    )
    assert reread_mode == CardAbHoldMode.ACTIVE.value
    assert reread_flag is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toggle_auto_add_only_relevant_in_session_blocked_under_hold(
    async_session: AsyncSession,
) -> None:
    """WRITE child: structural freeze → blocked, flag не меняется."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
        auto_add_only_relevant_phrase=False,
    )
    await async_session.commit()
    adv_id = adv.adv_id

    outcome = await (
        auto_add_only_relevant_phrase_toggle.toggle_auto_add_only_relevant_phrase_in_session(
            async_session, adv_id=adv_id, new_status=True
        )
    )
    assert outcome.blocked is True
    assert outcome.mutated is False

    async_session.expire_all()
    flag = await async_session.scalar(
        select(AdvSetting.auto_add_only_relevant_phrase).where(
            AdvSetting.adv_id == adv_id
        )
    )
    assert flag is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_toggle_auto_add_only_relevant_in_session_mutates_when_hold_off(
    async_session: AsyncSession,
) -> None:
    """WRITE child: Hold OFF → mutate + re-read persisted flag."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=None,
        auto_add_only_relevant_phrase=False,
    )
    await async_session.commit()
    adv_id = adv.adv_id

    outcome = await (
        auto_add_only_relevant_phrase_toggle.toggle_auto_add_only_relevant_phrase_in_session(
            async_session, adv_id=adv_id, new_status=True
        )
    )
    assert outcome.blocked is False
    assert outcome.mutated is True

    async_session.expire_all()
    flag = await async_session.scalar(
        select(AdvSetting.auto_add_only_relevant_phrase).where(
            AdvSetting.adv_id == adv_id
        )
    )
    assert flag is True
