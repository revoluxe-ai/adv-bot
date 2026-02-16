import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock

from app.client_bot.user_interface.handlers.individual_keywords_target_place_toggle import (
    toggle_individual_keywords_target_place,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm


def _make_callback(adv_id: int, new_status: bool) -> tuple[SimpleNamespace, SimpleNamespace]:
    callback_query = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=42))
    )
    callback_data = SimpleNamespace(adv_id=adv_id, new_status=new_status)
    return callback_query, callback_data


async def _create_test_adv(
    async_session,
    *,
    balance: float,
    bonus: float,
    individual_mode: bool = False,
) -> tuple[AdvSetting, WBCabinet]:
    # Ensure the session fixture is used so test database is prepared before inserting
    _ = async_session
    wb_cabinet = WBCabinet(
        shop_id=str(uuid.uuid4()),
        expiration_time=datetime.now() + timedelta(days=7),
        balance=balance,
        bonus=bonus,
    )
    search_adv = AdvSetting(
        adv_id=(uuid.uuid4().int & ((1 << 62) - 1)),
        name="search_adv",
        wb_cabinet=wb_cabinet,
        active_status="started",
        bot_active=False,
    )
    adv_setting = AdvSetting(
        adv_id=uuid.uuid4().int & ((1 << 62) - 1),
        name="test_indiv_bot",
        active_status="started",
        bot_active=True,
        wb_cabinet=wb_cabinet,
        individual_keywords_target_place_mode=individual_mode,
        automatic_version=1,
        auto_update_white_list=False,
        auto_update_target_place=False,
    )
    adv_setting._search_adv_id = search_adv.adv_id
    async with sm() as session:
        session.add_all([wb_cabinet, search_adv, adv_setting])
        await session.flush()
        await session.commit()
    return adv_setting, wb_cabinet


async def _fetch_adv(adv_id: int) -> AdvSetting | None:
    async with sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
        return await session.scalar(stmt)


@pytest.mark.asyncio
async def test_toggle_requires_balance(async_session):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=1.0, bonus=0.0, individual_mode=False
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, True)
    bot = AsyncMock()

    await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(adv_setting.adv_id)
    assert updated is not None
    assert not updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert "Недостаточно средств" in send_text
    assert bot.send_message.await_count == 1


@pytest.mark.asyncio
async def test_toggle_enables_when_balance_sufficient(async_session):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=1000.0, bonus=0.0, individual_mode=False
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, True)
    bot = AsyncMock()

    await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(adv_setting.adv_id)
    assert updated is not None
    assert updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert send_text == "Инд. места КЗ включены"


@pytest.mark.asyncio
async def test_toggle_disables_without_balance_check(async_session):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=0.0, bonus=0.0, individual_mode=True
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, False)
    bot = AsyncMock()

    await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(adv_setting.adv_id)
    assert updated is not None
    assert not updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert send_text == "Инд. места КЗ выключены"
