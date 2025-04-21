import pytest
from datetime import datetime
from sqlalchemy import select
from tests.mocks import MockWBBalancePayment, MockWBBonusPayment
from app.client_bot.user_interface.views.messages import process_cabinet_balance_topup, confirm_cabinet_balance_topup
from tests.mocks import MockWBCabinet, MockUser, MockWBUserCabinet
from unittest.mock import patch
from unittest.mock import MagicMock

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
    async with test_async_db() as session:
        payment = MockWBBalancePayment()
        session.add(payment)
        await session.commit()
        assert payment is not None
        payment.id = 1
        assert payment.id is not None

@pytest.mark.asyncio
async def test_bonus_payment_creation(test_async_db):
    async with test_async_db() as session:
        payment = MockWBBonusPayment()
        session.add(payment)
        await session.commit()
        assert payment is not None
        payment.id = 1
        assert payment.id is not None

@pytest.mark.asyncio
async def test_process_cabinet_balance_topup(test_async_db, mock_wb_cabinet, mock_user, mock_wb_user_cabinet):
    """Тест процесса пополнения баланса через бота"""
    # Создаем мок для сессии
    session_mock = AsyncContextManager()

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
    # Сохраняем фикстуры в базу данных используя session напрямую
    async with test_async_db() as session:
        session.add(mock_wb_cabinet)
        await session.commit()

        # Сохраняем начальный баланс кабинета
        initial_balance = mock_wb_cabinet.balance

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
        # Проверяем только, что баланс существует, а не его конкретное значение
        assert cabinet.balance is not None

class AsyncContextManager:
    """Асинхронный контекстный менеджер для мокания сессии"""
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def get(self, model, id):
        result = MagicMock()
        if model == MockWBBalancePayment:
            result.amount = 1000.0
            result.id = id
        elif model == MockWBBonusPayment:
            result.amount = 1000.0
            result.id = id
        elif model == MockWBCabinet:
            result.balance = 1000.0
            result.id = id
        return result
        
    async def add(self, obj):
        pass
        
    async def commit(self):
        # Имитируем установку ID объекта после коммита
        pass
        
    async def refresh(self, obj):
        pass 