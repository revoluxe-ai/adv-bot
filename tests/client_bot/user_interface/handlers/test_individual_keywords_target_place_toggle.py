"""Destructive PG-тесты toggle individual_keywords_target_place_mode.

Enable-path вызывает latch-backed Pricer; изолируем leg_latch от
process-global ``get_redis_client()`` singleton (order-dependent event loop).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.individual_keywords_target_place_toggle import (
    toggle_individual_keywords_target_place,
)
from app.modules.billing.leg_latch import LegLatchManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = pytest.mark.destructive_local


@contextmanager
def _isolated_leg_latch_patch() -> Iterator[LegLatchManager]:
    """Подменить latch-backed preview на FakeRedis вместо live singleton."""
    latch = LegLatchManager(FakeRedis())
    fixed_utc = datetime.now(timezone.utc).date()

    def _resolve(
        *,
        leg_latch: LegLatchManager | None = None,
        utc_date: date | None = None,
    ) -> tuple[LegLatchManager, date]:
        return latch, utc_date or fixed_utc

    with patch(
        "app.modules.billing.pricer.pricer.resolve_tariff_preview_latch_context",
        side_effect=_resolve,
    ):
        yield latch
def _make_callback(adv_id: int, new_status: bool) -> tuple[SimpleNamespace, SimpleNamespace]:
    callback_query = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=42))
    )
    callback_data = SimpleNamespace(adv_id=adv_id, new_status=new_status)
    return callback_query, callback_data


def _small_adv_id() -> int:
    """Return adv_id in int32 range to avoid PostgreSQL/asyncpg int32 range errors."""
    return (uuid.uuid4().int & 0x7FFF_FFFF) or 1


class _MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        pass


async def _create_test_adv(
    async_session: AsyncSession,
    *,
    balance: float,
    bonus: float,
    individual_mode: bool = False,
) -> tuple[AdvSetting, WBCabinet]:
    wb_cabinet = WBCabinet(
        shop_id=str(uuid.uuid4()),
        expiration_time=datetime.now() + timedelta(days=7),
        balance=balance,
        bonus=bonus,
    )
    search_adv_id = _small_adv_id()
    search_adv = AdvSetting(
        adv_id=search_adv_id,
        name="search_adv",
        wb_cabinet=wb_cabinet,
        active_status="started",
        bot_active=False,
    )
    adv_setting = AdvSetting(
        adv_id=_small_adv_id(),
        name="test_indiv_bot",
        active_status="started",
        bot_active=True,
        wb_cabinet=wb_cabinet,
        individual_keywords_target_place_mode=individual_mode,
        auto_update_white_list=False,
        auto_update_target_place=False,
    )
    adv_setting._search_adv_id = search_adv_id
    async_session.add_all([wb_cabinet, search_adv, adv_setting])
    await async_session.flush()
    await async_session.commit()
    return adv_setting, wb_cabinet


async def _fetch_adv(session: AsyncSession, adv_id: int) -> AdvSetting | None:
    stmt = select(AdvSetting).where(AdvSetting.adv_id == adv_id)
    return await session.scalar(stmt)


@pytest.mark.asyncio
async def test_toggle_requires_balance(async_session: AsyncSession):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=1.0, bonus=0.0, individual_mode=False
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, True)
    bot = AsyncMock()

    mock_sm = _MockSessionMaker(async_session)
    # Недостаточно средств: баланс+бонус меньше требуемой цены
    async def _fake_balance(_cabinet_id: int) -> tuple[float, float]:
        return (0.0, 0.0)

    with (
        patch(
            "app.client_bot.user_interface.handlers.individual_keywords_target_place_toggle.sm",
            mock_sm,
        ),
        patch(
            "app.modules.billing.paid_option_check.balance_manager.get_cabinet_balance_and_bonuses",
            _fake_balance,
        ),
        _isolated_leg_latch_patch(),
    ):
        await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(async_session, adv_setting.adv_id)
    assert updated is not None
    assert not updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert "Недостаточно средств" in send_text
    assert bot.send_message.await_count == 1


@pytest.mark.asyncio
async def test_toggle_enables_when_balance_sufficient(async_session: AsyncSession):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=1000.0, bonus=0.0, individual_mode=False
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, True)
    bot = AsyncMock()

    mock_sm = _MockSessionMaker(async_session)
    # Достаточно средств: баланс+бонус покрывают цену
    async def _fake_balance(_cabinet_id: int) -> tuple[float, float]:
        return (10000.0, 0.0)

    with (
        patch(
            "app.client_bot.user_interface.handlers.individual_keywords_target_place_toggle.sm",
            mock_sm,
        ),
        patch(
            "app.modules.billing.paid_option_check.balance_manager.get_cabinet_balance_and_bonuses",
            _fake_balance,
        ),
        _isolated_leg_latch_patch(),
    ):
        await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(async_session, adv_setting.adv_id)
    assert updated is not None
    assert updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert send_text == "Инд. места КЗ включены"


@pytest.mark.asyncio
async def test_toggle_disables_without_balance_check(async_session: AsyncSession):
    adv_setting, _ = await _create_test_adv(
        async_session, balance=0.0, bonus=0.0, individual_mode=True
    )
    callback_query, callback_data = _make_callback(adv_setting.adv_id, False)
    bot = AsyncMock()

    mock_sm = _MockSessionMaker(async_session)
    with patch(
        "app.client_bot.user_interface.handlers.individual_keywords_target_place_toggle.sm",
        mock_sm,
    ), patch(
        "app.modules.balance_manager.balance_service.sm",
        mock_sm,
    ):
        await toggle_individual_keywords_target_place(callback_query, callback_data, bot)

    updated = await _fetch_adv(async_session, adv_setting.adv_id)
    assert updated is not None
    assert not updated.individual_keywords_target_place_mode
    send_text = bot.send_message.await_args.args[1]
    assert send_text == "Инд. места КЗ выключены"
