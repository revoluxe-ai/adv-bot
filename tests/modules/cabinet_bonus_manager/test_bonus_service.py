from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.cabinet_bonus_manager import bonus_service


pytestmark = pytest.mark.asyncio


def _make_async_cm(session: AsyncMock):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@patch("app.modules.cabinet_bonus_manager.bonus_service.sm")
async def test_add_balance_creates_positive_balance_payment(mock_sm):
    add_calls: list[object] = []
    session = AsyncMock()
    session.begin = AsyncMock()
    session.get = AsyncMock(return_value=MagicMock(id=10))
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    mock_sm.return_value = _make_async_cm(session)

    result = await bonus_service.add_balance(
        wb_cabinet_original_id=10,
        amount=150.0,
        admin_user_id=1,
        description="manual",
    )

    assert result is True
    assert len(add_calls) == 1
    payment = add_calls[0]
    assert payment.amount == 150.0
    assert payment.operation_type == "add"
    session.commit.assert_awaited_once()


@patch("app.modules.cabinet_bonus_manager.bonus_service.get_cabinet_by_id")
@patch("app.modules.cabinet_bonus_manager.bonus_service.sm")
async def test_subtract_balance_creates_negative_balance_payment(mock_sm, mock_get_cabinet):
    add_calls: list[object] = []
    mock_get_cabinet.return_value = MagicMock(id=10, calculated_balance=500.0)

    session = AsyncMock()
    session.begin = AsyncMock()
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()
    mock_sm.return_value = _make_async_cm(session)

    result = await bonus_service.subtract_balance(
        cabinet_id=10,
        amount=120.0,
        admin_user_id=1,
        description="manual",
    )

    assert result is True
    assert len(add_calls) == 1
    payment = add_calls[0]
    assert payment.amount == -120.0
    assert payment.operation_type == "subtract"


@patch("app.modules.cabinet_bonus_manager.bonus_service.get_cabinet_by_id")
async def test_subtract_total_with_bonus_priority_spends_only_bonus(mock_get_cabinet):
    mock_get_cabinet.return_value = MagicMock(
        id=10,
        calculated_bonus=300.0,
        calculated_balance=500.0,
    )
    add_calls: list[object] = []
    session = AsyncMock()
    session.begin = AsyncMock()
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()

    with patch("app.modules.cabinet_bonus_manager.bonus_service.sm") as mock_sm:
        mock_sm.return_value = _make_async_cm(session)
        result, bonus_spent, balance_spent = (
            await bonus_service.subtract_total_with_bonus_priority(
                cabinet_id=10,
                amount=200.0,
                admin_user_id=1,
                description="manual",
            )
        )

    assert result is True
    assert bonus_spent == 200.0
    assert balance_spent == 0.0
    assert len(add_calls) == 1
    assert add_calls[0].amount == -200.0


@patch("app.modules.cabinet_bonus_manager.bonus_service.get_cabinet_by_id")
async def test_subtract_total_with_bonus_priority_spends_bonus_then_balance(mock_get_cabinet):
    mock_get_cabinet.return_value = MagicMock(
        id=10,
        calculated_bonus=80.0,
        calculated_balance=500.0,
    )
    add_calls: list[object] = []
    session = AsyncMock()
    session.begin = AsyncMock()
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()

    with patch("app.modules.cabinet_bonus_manager.bonus_service.sm") as mock_sm:
        mock_sm.return_value = _make_async_cm(session)
        result, bonus_spent, balance_spent = (
            await bonus_service.subtract_total_with_bonus_priority(
                cabinet_id=10,
                amount=200.0,
                admin_user_id=1,
                description="manual",
            )
        )

    assert result is True
    assert bonus_spent == 80.0
    assert balance_spent == 120.0
    assert len(add_calls) == 2
    amounts = sorted([float(obj.amount) for obj in add_calls])
    assert amounts == [-120.0, -80.0]


@patch("app.modules.cabinet_bonus_manager.bonus_service.get_cabinet_by_id")
async def test_subtract_total_with_bonus_priority_allows_negative_balance(mock_get_cabinet):
    mock_get_cabinet.return_value = MagicMock(
        id=10,
        calculated_bonus=50.0,
        calculated_balance=40.0,
    )
    add_calls: list[object] = []
    session = AsyncMock()
    session.begin = AsyncMock()
    session.add = lambda obj: add_calls.append(obj)
    session.commit = AsyncMock()

    with patch("app.modules.cabinet_bonus_manager.bonus_service.sm") as mock_sm:
        mock_sm.return_value = _make_async_cm(session)
        result, bonus_spent, balance_spent = (
            await bonus_service.subtract_total_with_bonus_priority(
                cabinet_id=10,
                amount=100.0,
                admin_user_id=1,
                description="manual",
            )
        )

    assert result is True
    assert bonus_spent == 50.0
    assert balance_spent == 50.0
    assert len(add_calls) == 2
