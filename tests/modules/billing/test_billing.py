"""Tests for billing per-cabinet daily charge logic."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing import billing
from app.modules.billing.pricer import Pricer
from app.modules.billing.pricer.pricer import TariffDetails, TariffMode
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

pytestmark = pytest.mark.asyncio


def _tariff_details(total_per_day: float, count: float = 1.0) -> TariffDetails:
    return TariffDetails(
        mode=TariffMode.AUTO,
        count=count,
        price_per_adv=100.0,
        total_per_month=100.0,
        total_per_day=total_per_day,
    )


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_pricer():
    pr = AsyncMock(spec=Pricer)
    pr.get_tariff_details.return_value = _tariff_details(75.0)
    return pr


@pytest.fixture
def mock_redis_manager():
    mgr = AsyncMock()
    mgr.get_billing_process_for_day.return_value = False
    mgr.set_billing_process_for_day.return_value = None
    latch = AsyncMock()
    latch.record_sample.return_value = 0.5
    latch.get_billable_weight.return_value = 0.5
    mgr.leg_latch = MagicMock(return_value=latch)
    return mgr


def _paid_like_adv(*, adv_id: int = 1, bot_active: bool = True) -> MagicMock:
    """Build a campaign that looks like explicit PAID auto-management before grace."""
    adv = MagicMock(spec=AdvSetting)
    adv.id = adv_id
    adv.bot_active = bot_active
    adv.automatic_version = 3
    adv.bidder_active = True
    adv.bidder_for_auto = True
    adv.white_list_mode = WhiteListMode.REPLACE_ON_TRIM
    adv.auto_update_white_list = True
    adv.auto_update_target_place = True
    adv.wb_cabinet_id = 100
    adv.payments = []
    return adv


def _assert_free_mode_overlay(adv: MagicMock) -> None:
    """Lock grace-exceeded → FREE transition via apply_free_mode_transition."""
    assert adv.bot_active is False
    assert adv.automatic_version == 2
    assert adv.bidder_active is False
    assert adv.bidder_for_auto is False
    assert adv.auto_update_white_list is False
    assert adv.auto_update_target_place is False
    assert adv.white_list_mode == WhiteListMode.ABOVE_MIN_RATING


@pytest.fixture
def active_adv():
    return _paid_like_adv(adv_id=1, bot_active=True)


@pytest.fixture
def inactive_adv():
    return _paid_like_adv(adv_id=2, bot_active=False)


def _make_cabinet(
    cabinet_id=100,
    shop_id=123,
    bonus=100.0,
    balance=50.0,
    advs=None,
    balance_went_negative_at=None,
):
    cab = MagicMock()
    cab.id = cabinet_id
    cab.shop_id = shop_id
    cab.calculated_bonus = bonus
    cab.calculated_balance = balance
    cab.balance_payments = []
    cab.bonus_payments = []
    cab.adv_settings = advs or []
    cab.balance_went_negative_at = balance_went_negative_at
    return cab


async def test_process_single_cabinet_bonus_success(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    cab = _make_cabinet(bonus=200.0, balance=0.0, advs=[active_adv])

    # Патчим загрузку кабинета
    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ):
        # scalar для подсчета уже существующих платежей -> нули
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
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
    mock_pricer.get_tariff_details.assert_awaited_once()


async def test_process_single_cabinet_insufficient_funds_first_day_negative(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """Недостаточно средств, balance_went_negative_at=None: первый день в минус — списываем в минус, кампании активны."""
    cab = _make_cabinet(
        bonus=0.0, balance=10.0, advs=[active_adv], balance_went_negative_at=None
    )
    mock_pricer.get_tariff_details.return_value = _tariff_details(100.0)

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_grace_exceeded", new=AsyncMock()), patch.object(
        billing, "_notify_days_until_block", new=AsyncMock()
    ):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 2, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is True
    assert result["reason"] == "success"
    assert active_adv.bot_active is True
    assert cab.balance_went_negative_at is not None


async def test_process_single_cabinet_grace_exceeded_deactivates(
    mock_session, mock_pricer, mock_redis_manager, active_adv, inactive_adv
):
    """Grace exceeded: active paid campaigns switch to FREE overlay; neg_at kept.

    Protects against regressing to a partial deactivate (only bot_active /
    whitelist / target-place flags) without V3→V2 FREE conversion.
    """
    from datetime import timezone

    neg_at = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    cab = _make_cabinet(
        bonus=0.0,
        balance=-800.0,
        advs=[active_adv, inactive_adv],
        balance_went_negative_at=neg_at,
    )
    mock_pricer.get_price_for_day_for_shop.return_value = 100.0
    # balance_after_charge = -800 - 100 = -900 < -700 → deactivate

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_grace_exceeded", new=AsyncMock()):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 9, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is False
    assert result["reason"] == "deactivated"
    _assert_free_mode_overlay(active_adv)
    # Already-free / inactive campaigns are not re-touched by the grace path.
    assert inactive_adv.bot_active is False
    assert inactive_adv.automatic_version == 3
    assert inactive_adv.bidder_active is True
    assert inactive_adv.white_list_mode == WhiteListMode.REPLACE_ON_TRIM
    assert cab.balance_went_negative_at is not None  # не сбрасываем (фикс бага)


async def test_process_single_cabinet_negative_within_limit_charges(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """В пределах лимита минуса: списание в минус, кампании остаются активными."""
    cab = _make_cabinet(
        bonus=0.0, balance=-200.0, advs=[active_adv], balance_went_negative_at=None
    )
    mock_pricer.get_tariff_details.return_value = _tariff_details(100.0)
    # balance_after_charge = -300, limit -700 → charge

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_days_until_block", new=AsyncMock()):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 2, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is True
    assert result["reason"] == "success"
    assert active_adv.bot_active is True


async def test_process_single_cabinet_negative_at_boundary_charges(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """Граница ровно на лимите (-700): списание допускается."""
    cab = _make_cabinet(
        bonus=0.0, balance=-600.0, advs=[active_adv], balance_went_negative_at=None
    )
    mock_pricer.get_tariff_details.return_value = _tariff_details(100.0)
    # balance_after_charge = -700, limit -700 → still allowed (>= -700 in sense of not <)

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_days_until_block", new=AsyncMock()):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 2, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is True
    assert result["reason"] == "success"
    assert active_adv.bot_active is True


async def test_process_single_cabinet_grace_exceeded_rerun_no_charge(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """Повторный grace: FREE overlay, без списания, neg_at не сбрасывается."""
    from datetime import timezone

    neg_at = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    cab = _make_cabinet(
        bonus=0.0,
        balance=-800.0,
        advs=[active_adv],
        balance_went_negative_at=neg_at,
    )
    mock_pricer.get_tariff_details.return_value = _tariff_details(100.0)
    add_count_before = mock_session.add.call_count

    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_grace_exceeded", new=AsyncMock()):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 9, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["payment_successful"] is False
    assert result["reason"] == "deactivated"
    _assert_free_mode_overlay(active_adv)
    assert cab.balance_went_negative_at is not None
    # Не должно быть новых add (WBBalancePayment / AdvPayment за этот день)
    assert mock_session.add.call_count == add_count_before


async def test_process_single_cabinet_negative_calls_notify_days_until_block(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """При списании в минус в пределах лимита вызывается _notify_days_until_block с верным days_left."""
    cab = _make_cabinet(
        bonus=0.0, balance=10.0, advs=[active_adv], balance_went_negative_at=None
    )
    mock_pricer.get_tariff_details.return_value = _tariff_details(100.0)
    # balance_after_charge = -90, max_allowed_negative = 700, room = 610, days_left = 6

    notify_mock = AsyncMock()
    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_notify_grace_exceeded", new=AsyncMock()), patch.object(
        billing, "_notify_days_until_block", new=notify_mock
    ):
        mock_session.scalar.return_value = 0
        await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 2, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    notify_mock.assert_awaited_once_with(cab.id, 6)


async def test_process_single_cabinet_zero_price(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    cab = _make_cabinet(bonus=50.0, balance=50.0, advs=[active_adv])
    mock_pricer.get_tariff_details.return_value = _tariff_details(0.0, count=0.0)
    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 3, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["reason"] == "zero_price"
    assert result["payment_successful"] is False


async def test_process_single_cabinet_stale_redis_flag_still_charges_when_db_clean(
    mock_session, mock_pricer, mock_redis_manager, active_adv
):
    """Stale billing:processed must not block charge when DB has no debit today."""
    cab = _make_cabinet(bonus=200.0, balance=0.0, advs=[active_adv])
    mock_redis_manager.get_billing_process_for_day.return_value = True
    with patch.object(
        billing, "_load_cabinet_with_relations", new=AsyncMock(return_value=cab)
    ), patch.object(billing, "_safe_commit", new=AsyncMock(return_value=True)):
        mock_session.scalar.return_value = 0
        result = await billing.__process_single_cabinet(
            session=mock_session,
            cabinet_id=cab.id,
            current_dt=datetime.datetime(2024, 1, 4, 10, 0, 0),
            pricer=mock_pricer,
            redis_manager=mock_redis_manager,
        )
    assert result["reason"] != "redis_flag_skip"
    assert result["payment_successful"] is True
    mock_session.add.assert_called()


async def test__process_payment_for_advs_invokes_single(
    mock_pricer, mock_redis_manager
):
    # Патчим список id и сам обработчик одного кабинета
    with patch.object(
        billing, "_fetch_active_cabinet_ids", new=AsyncMock(return_value=[10, 20])
    ):
        single_results = [
            {"cabinet_id": 10, "processed": True},
            {"cabinet_id": 20, "processed": True},
        ]
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
    mock_execute_result.all.return_value = [
        (1,),
        (2,),
        (3,),
    ]  # обычный Mock, не AsyncMock
    mock_session.execute.return_value = mock_execute_result
    ids = await billing._fetch_active_cabinet_ids(mock_session)
    assert ids == [1, 2, 3]
