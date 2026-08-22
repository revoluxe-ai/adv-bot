"""Integration coverage for client_bot PG seams (add phrases / hard_status / update_keywords).

Проверяет injectable ``*_in_session`` / session-injected writers через живой
``async_session`` + SQL re-read. Не marker ``fast``; live DB via fixture.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.user_interface.handlers import add_white_phrases, keyword_settings
from app.client_bot.user_interface.handlers.adv_setting.utils.keyword_updater import (
    update_keywords,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Минимальный WBCabinet для seam-тестов."""
    cabinet = WBCabinet(
        shop_id=f"phrases_seam_{uuid.uuid4().hex}",
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
    bot_active: bool = True,
) -> AdvSetting:
    """Минимальный AdvSetting с опциональным A/B Hold mode."""
    adv = AdvSetting(
        adv_id=int(uuid.uuid4().int % 1_000_000) + 50_000,
        name="phrases-seam-test",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=bot_active,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=75,
        card_ab_hold_mode=hold_mode,
    )
    async_session.add(adv)
    await async_session.flush()
    return adv


async def _create_user_cabinet(
    async_session: AsyncSession,
    cabinet: WBCabinet,
) -> WBUserCabinet:
    """User + WBUserCabinet для update_keywords scope."""
    user = User(
        user_telegram_id=int(uuid.uuid4().int % 1_000_000_000),
        username=f"seam_{uuid.uuid4().hex[:8]}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()
    uc = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="phrases-seam-uc",
    )
    async_session.add(uc)
    await async_session.flush()
    return uc


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_adv_card_ab_hold_mode_in_session_reads_mode(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child: ``load_adv_card_ab_hold_mode_in_session`` + re-select."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    await async_session.commit()

    mode = await add_white_phrases.load_adv_card_ab_hold_mode_in_session(
        async_session, adv.id
    )
    assert mode == CardAbHoldMode.ACTIVE.value

    reread = await async_session.scalar(
        select(AdvSetting.card_ab_hold_mode).where(AdvSetting.id == adv.id)
    )
    assert reread == CardAbHoldMode.ACTIVE.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reset_white_list_in_session_blocked_under_hold(
    async_session: AsyncSession,
) -> None:
    """WRITE child: structural freeze → blocked, hard_status не меняется."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.PENDING_SETUP.value,
    )
    kw = KeywordSetting(
        text="white-held",
        adv_setting_id=adv.id,
        hard_status=2,
        strategy_mode=KeywordStrategyMode.MIN_CPA,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await add_white_phrases.reset_white_list_in_session(
        async_session, adv_setting_id=adv.id
    )
    assert outcome.blocked is True
    assert outcome.mutated is False

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    assert hard == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reset_white_list_in_session_mutates_when_hold_off(
    async_session: AsyncSession,
) -> None:
    """WRITE child: Hold OFF → WHITE_LIST→AUTO + SQL re-read."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.OFF.value,
    )
    kw = KeywordSetting(
        text="white-free",
        adv_setting_id=adv.id,
        hard_status=2,
        strategy_mode=KeywordStrategyMode.MIN_CPA,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await add_white_phrases.reset_white_list_in_session(
        async_session, adv_setting_id=adv.id
    )
    assert outcome.blocked is False
    assert outcome.mutated is True

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    assert hard == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reset_non_relevant_phrases_in_session_blocked_under_hold(
    async_session: AsyncSession,
) -> None:
    """WRITE child: freeze → BLACK_LIST не сбрасывается."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    kw = KeywordSetting(
        text="black-held",
        adv_setting_id=adv.id,
        hard_status=0,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await add_white_phrases.reset_non_relevant_phrases_in_session(
        async_session, adv_setting_id=adv.id
    )
    assert outcome.blocked is True

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    assert hard == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reset_non_relevant_phrases_in_session_mutates_when_hold_off(
    async_session: AsyncSession,
) -> None:
    """WRITE child: Hold OFF → BLACK_LIST→AUTO + SQL re-read."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.OFF.value,
    )
    kw = KeywordSetting(
        text="black-free",
        adv_setting_id=adv.id,
        hard_status=0,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await add_white_phrases.reset_non_relevant_phrases_in_session(
        async_session, adv_setting_id=adv.id
    )
    assert outcome.blocked is False
    assert outcome.mutated is True

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    mode = await async_session.scalar(
        select(KeywordSetting.strategy_mode).where(KeywordSetting.id == kw_id)
    )
    assert hard == 1
    assert mode == KeywordStrategyMode.OFF


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_adv_setting_in_session_reads_row(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child: ``load_adv_setting_in_session`` + SQL re-read."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.OFF.value,
    )
    await async_session.commit()

    loaded = await add_white_phrases.load_adv_setting_in_session(
        async_session, adv.id
    )
    assert loaded is not None
    assert loaded.id == adv.id
    assert loaded.adv_id == adv.adv_id

    reread_id = await async_session.scalar(
        select(AdvSetting.id).where(AdvSetting.id == adv.id)
    )
    assert reread_id == adv.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_wb_user_cabinet_in_session_reads_row(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child: ``load_wb_user_cabinet_in_session`` + SQL re-read."""
    cabinet = await _create_cabinet(async_session)
    uc = await _create_user_cabinet(async_session, cabinet)
    await async_session.commit()

    loaded = await add_white_phrases.load_wb_user_cabinet_in_session(
        async_session, uc.id
    )
    assert loaded is not None
    assert loaded.id == uc.id
    assert loaded.wb_cabinet_id == cabinet.id

    reread_name = await async_session.scalar(
        select(WBUserCabinet.name).where(WBUserCabinet.id == uc.id)
    )
    assert reread_name == "phrases-seam-uc"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_keyword_hard_status_in_session_blocked_under_hold(
    async_session: AsyncSession,
) -> None:
    """WRITE child: freeze → kind=blocked, hard_status не меняется."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    kw = KeywordSetting(
        text="hs-held",
        adv_setting_id=adv.id,
        hard_status=1,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await keyword_settings.change_keyword_hard_status_in_session(
        async_session,
        keyword_setting_original_id=kw_id,
        new_hard_status=2,
    )
    assert outcome.kind == "blocked"

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    assert hard == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_keyword_hard_status_in_session_applies_when_hold_off(
    async_session: AsyncSession,
) -> None:
    """WRITE child: Hold OFF → hard_status=2 + SQL re-read."""
    cabinet = await _create_cabinet(async_session)
    adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.OFF.value,
    )
    kw = KeywordSetting(
        text="hs-free",
        adv_setting_id=adv.id,
        hard_status=1,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    async_session.add(kw)
    await async_session.commit()
    kw_id = kw.id

    outcome = await keyword_settings.change_keyword_hard_status_in_session(
        async_session,
        keyword_setting_original_id=kw_id,
        new_hard_status=2,
    )
    assert outcome.kind == "applied"

    async_session.expire_all()
    hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == kw_id)
    )
    assert hard == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_keywords_skips_structural_freeze_and_rereads(
    async_session: AsyncSession,
) -> None:
    """``update_keywords`` injected session: held campaign BLACK_LIST intact."""
    cabinet = await _create_cabinet(async_session)
    uc = await _create_user_cabinet(async_session, cabinet)
    free_adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.OFF.value,
        bot_active=True,
    )
    held_adv = await _create_adv(
        async_session,
        cabinet=cabinet,
        hold_mode=CardAbHoldMode.ACTIVE.value,
        bot_active=True,
    )
    free_kw = KeywordSetting(
        text="free-black",
        adv_setting_id=free_adv.id,
        hard_status=const.BLACK_LIST,
        strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    held_kw = KeywordSetting(
        text="held-black",
        adv_setting_id=held_adv.id,
        hard_status=const.BLACK_LIST,
        strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
    )
    async_session.add_all([free_kw, held_kw])
    await async_session.commit()
    free_id, held_id = free_kw.id, held_kw.id

    result = await update_keywords(async_session, uc.id)
    await async_session.commit()

    assert result.skipped_count == 1
    async_session.expire_all()
    free_hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == free_id)
    )
    held_hard = await async_session.scalar(
        select(KeywordSetting.hard_status).where(KeywordSetting.id == held_id)
    )
    free_mode = await async_session.scalar(
        select(KeywordSetting.strategy_mode).where(KeywordSetting.id == free_id)
    )
    assert free_hard == const.AUTO_MODE
    assert free_mode == KeywordStrategyMode.OFF
    assert held_hard == const.BLACK_LIST
