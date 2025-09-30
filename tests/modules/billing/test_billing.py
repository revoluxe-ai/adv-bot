"""Tests for billing per-cabinet daily charge logic."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_pricer():
    pr = AsyncMock(spec=Pricer)
    pr.get_price_for_day_for_shop.return_value = 75.0
    return pr


@pytest.fixture
def mock_redis_manager():
    mgr = AsyncMock()
    mgr.get_billing_process_for_day.return_value = False
    mgr.set_billing_process_for_day.return_value = None
    return mgr


@pytest.fixture
def active_adv():
    adv = MagicMock(spec=AdvSetting)
    adv.id = 1
    adv.bot_active = True
    adv.auto_update_white_list = True
    adv.auto_update_target_place = True
    adv.wb_cabinet_id = 100
    adv.payments = []
    return adv


@pytest.fixture
def inactive_adv():
    adv = MagicMock(spec=AdvSetting)
    adv.id = 2
    adv.bot_active = False
    adv.wb_cabinet_id = 100
    adv.payments = []
    return adv


def _make_cabinet(cabinet_id=100, shop_id=123, bonus=100.0, balance=50.0, advs=None):
    cab = MagicMock()
    cab.id = cabinet_id
    cab.shop_id = shop_id
    cab.calculated_bonus = bonus
    cab.calculated_balance = balance
    cab.balance_payments = []
    cab.bonus_payments = []
    cab.adv_settings = advs or []
    return cab


async def test_process_single_cabinet_bonus_success(mock_session, mock_pricer, mock_redis_manager, active_adv):
    cab = _make_cabinet(bonus=200.0, balance=0.0, advs=[active_adv])

    # Патчим загрузку кабинета
    with patch.object(billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)):
        # scalar для подсчета уже существующих платежей -> нули
        mock_session.scalar.return_value = 0
        result = await billing._process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 1, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is True
    assert result["processed"] is True
    # Был добавлен WBBonusPayment и AdvPayment => минимум 2 add вызова
    assert mock_session.add.call_count >= 2
    mock_pricer.get_price_for_day_for_shop.assert_awaited_once()


async def test_process_single_cabinet_insufficient_funds(mock_session, mock_pricer, mock_redis_manager, active_adv):
    cab = _make_cabinet(bonus=0.0, balance=10.0, advs=[active_adv])
    mock_pricer.get_price_for_day_for_shop.return_value = 100.0

    with patch.object(billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)):
        mock_session.scalar.return_value = 0
        result = await billing._process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 2, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is False
    assert result["reason"] in {"deactivated", "no_payment"}
    # Кампания деактивирована
    assert active_adv.bot_active is False


async def test_process_single_cabinet_zero_price(mock_session, mock_pricer, mock_redis_manager, active_adv):
    cab = _make_cabinet(bonus=50.0, balance=50.0, advs=[active_adv])
    mock_pricer.get_price_for_day_for_shop.return_value = 0.0
    with patch.object(billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)):
        mock_session.scalar.return_value = 0
        result = await billing._process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 3, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["reason"] == "zero_price"
    assert result["payment_successful"] is False


async def test_process_single_cabinet_already_flagged_in_redis(mock_session, mock_pricer, mock_redis_manager,
                                                               active_adv):
    cab = _make_cabinet(bonus=200.0, balance=0.0, advs=[active_adv])
    mock_redis_manager.get_billing_process_for_day.return_value = True
    result = await billing._process_single_cabinet(
        session=mock_session,
        cabinet_id=cab.id,
        current_dt=datetime.datetime(2024, 1, 4, 10, 0, 0),
        pricer=mock_pricer,
        redis_manager=mock_redis_manager,
    )
    assert result["reason"] == "redis_flag_skip"
    mock_session.add.assert_not_called()


async def test__process_payment_for_advs_invokes_single(mock_pricer, mock_redis_manager):
    # Патчим список id и сам обработчик одного кабинета
    with patch.object(billing, "_fetch_active_cabinet_ids", new=AsyncMock(return_value=[10, 20])):
        single_results = [{"cabinet_id": 10, "processed": True}, {"cabinet_id": 20, "processed": True}]
        single_mock = AsyncMock(side_effect=single_results)
        with patch.object(billing, "_process_single_cabinet", new=single_mock):
            # Патчим session maker sm -> два использования (read_only True/False)
            class DummyCtx:
                def __init__(self):
                    self._enter_calls = 0

                async def __aenter__(self):
                    return AsyncMock(spec=AsyncSession)

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            with patch.object(billing, "sm", new=MagicMock(return_value=DummyCtx())):
                await billing._process_payment_for_advs(
                    current_date_time=datetime.datetime(2024, 1, 5, 12, 0, 0),
                    pricer=mock_pricer,
                    redis_manager=mock_redis_manager,
                )
    assert single_mock.call_count == 2
    called_ids = {c.kwargs["cabinet_id"] for c in single_mock.call_args_list}
    assert called_ids == {10, 20}


async def test_fetch_active_cabinet_ids_low_level(mock_session):
    # Проверяем что _fetch_active_cabinet_ids вытаскивает первую колонку
    mock_execute_result = MagicMock()
    mock_execute_result.all.return_value = [(1,), (2,), (3,)]  # обычный Mock, не AsyncMock
    mock_session.execute.return_value = mock_execute_result
    ids = await billing._fetch_active_cabinet_ids(mock_session)
    assert ids == [1, 2, 3]
