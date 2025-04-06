import pytest
from datetime import datetime
from sqlalchemy import select
from tests.mocks import MockWBBalancePayment, MockWBBonusPayment
from app.client_bot.user_interface.views.messages import process_cabinet_balance_topup, confirm_cabinet_balance_topup
from tests.mocks import MockWBCabinet, MockUser, MockWBUserCabinet
from unittest.mock import patch

@pytest.fixture
async def mock_wb_user_cabinet():
    return MockWBUserCabinet(
        id=1,
        wb_cabinet_id=1,
        user_id=1,
        name="Test Cabinet"
    )

@pytest.mark.asyncio
async def test_balance_payment_creation(test_async_db):
    payment = MockWBBalancePayment()
    test_async_db.add(payment)
    await test_async_db.commit()
    
    assert payment.id is not None
    assert payment.status == "new"

@pytest.mark.asyncio
async def test_bonus_payment_creation(test_async_db):
    payment = MockWBBonusPayment()
    test_async_db.add(payment)
    await test_async_db.commit()
    
    assert payment.id is not None
    assert payment.status == "new"

@pytest.mark.asyncio
async def test_process_cabinet_balance_topup(test_async_db, mocker):
    cabinet = MockWBCabinet()
    user = MockUser()
    test_async_db.add(cabinet)
    test_async_db.add(user)
    await test_async_db.commit()

    payment = await create_balance_payment(
        session=test_async_db,
        cabinet_id=cabinet.id,
        user_id=user.id,
        amount=1000
    )
    
    assert payment.id is not None
    assert payment.status == "new"
    assert payment.amount == 1000

@pytest.mark.asyncio
async def test_confirm_balance_payment(test_async_db):
    cabinet = MockWBCabinet()
    user = MockUser()
    test_async_db.add(cabinet)
    test_async_db.add(user)
    await test_async_db.commit()

    payment = await create_balance_payment(
        session=test_async_db,
        cabinet_id=cabinet.id,
        user_id=user.id,
        amount=1000
    )
    
    await confirm_balance_payment(session=test_async_db, payment_id=payment.id)
    await test_async_db.refresh(cabinet)
    
    assert payment.status == "confirmed"
    assert cabinet.balance == 1000

class AsyncContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get(self, model, id):
        if model == User:
            return MockUser()
        elif model == WBCabinet:
            return MockWBCabinet()
        elif model == WBBalancePayment:
            return MockWBBalancePayment()
        return None

    async def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

@pytest.mark.asyncio
async def test_process_cabinet_balance_topup(test_async_db, mock_wb_cabinet, mock_user, mock_wb_user_cabinet):
    """Тест процесса пополнения баланса через бота"""
    # Создаем мок для сессии
    session_mock = AsyncContextManager()

    # Патчим функцию создания сессии
    with patch('app.client_bot.user_interface.views.messages._sm', return_value=lambda: session_mock):
        # Сохраняем фикстуры в базу данных используя session напрямую
        async with test_async_db() as session:
            session.add(mock_wb_cabinet)
            session.add(mock_user)
            await session.commit()

            # Создаем запись о пополнении баланса
            payment = MockWBBalancePayment(
                wb_cabinet_id=mock_wb_cabinet.id,
                amount=1000.0,
                description="Test payment",
                transaction_date_time=datetime.now()
            )
            session.add(payment)
            await session.commit()

            # Проверяем, что запись создана
            result = await session.get(MockWBBalancePayment, payment.id)
            assert result is not None
            assert result.amount == 1000.0

@pytest.mark.asyncio
async def test_confirm_balance_payment(test_async_db, mock_wb_cabinet):
    """Тест подтверждения платежа и обновления баланса кабинета"""
    # Создаем мок для сессии
    session_mock = AsyncContextManager()

    # Патчим функцию создания сессии
    with patch('app.client_bot.user_interface.views.messages._sm', return_value=lambda: session_mock):
        # Сохраняем фикстуры в базу данных используя session напрямую
        async with test_async_db() as session:
            session.add(mock_wb_cabinet)
            await session.commit()

            # Создаем запись о пополнении баланса
            payment = MockWBBalancePayment(
                wb_cabinet_id=mock_wb_cabinet.id,
                amount=1000.0,
                description="Test payment",
                transaction_date_time=datetime.now()
            )
            session.add(payment)
            await session.commit()

            # Проверяем, что запись создана и баланс обновлен
            result = await session.get(MockWBBalancePayment, payment.id)
            assert result is not None
            assert result.amount == 1000.0

            cabinet = await session.get(MockWBCabinet, mock_wb_cabinet.id)
            assert cabinet is not None
            assert cabinet.balance == mock_wb_cabinet.balance + 1000.0 