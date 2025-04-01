import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
from tests.mocks import MockWBCabinet, MockWBUserCabinet, MockUser, MockWBToken, MockWBBalancePayment, MockWBBonusPayment
from tests.conftest import test_async_db



@pytest.mark.asyncio
async def test_get_access_for_wb_cabinet(test_async_db: AsyncSession):
    """Тестирование функции получения доступа к кабинету с учетом балансов и бонусов"""
    
    # Создаем пользователя
    user = MockUser(user_telegram_id=123, username="test_user")
    test_async_db.add(user)
    await test_async_db.flush()

    # Создаем кабинет с положительным балансом
    cabinet = MockWBCabinet(shop_id="123", balance=100.0, bonus=50.0)
    test_async_db.add(cabinet)
    await test_async_db.flush()

    # Создаем связь пользователя с кабинетом
    user_cabinet = MockWBUserCabinet(wb_cabinet_id=cabinet.id, user_id=user.id, name="test_cabinet")
    test_async_db.add(user_cabinet)
    await test_async_db.flush()

    # Добавляем токен
    token = MockWBToken(api_key="test_key", user_id=user.id, active=True, shop_id=cabinet.shop_id)
    test_async_db.add(token)
    await test_async_db.flush()

    # Добавляем платежи
    balance_payment = MockWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=100.0,
        transaction_date_time=datetime.now()
    )
    test_async_db.add(balance_payment)

    bonus_payment = MockWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=50.0,
        transaction_date_time=datetime.now(),
        operation_type="add"
    )
    test_async_db.add(bonus_payment)
    await test_async_db.flush()

    # Создаем второй кабинет с отрицательным балансом
    cabinet2 = MockWBCabinet(shop_id="456", balance=-100.0, bonus=0.0)
    test_async_db.add(cabinet2)
    await test_async_db.flush()

    # Получаем доступ к кабинету
    access = await get_access_for_wb_cabinet(cabinet.shop_id)
    
    # Добавляем отладочный вывод
    print(f"Информация о кабинете: {access}")
    if access:
        print(f"ShopId кабинета: {access.wb_cabinet.shop_id}")
        print(f"Бонус кабинета: {access.wb_cabinet.bonus}")
        print(f"Токены кабинета: {access.tokens}")
        if access.tokens:
            print(f"API ключ первого токена: {access.tokens[0].api_key}")
    
    # Проверяем результаты
    assert access is not None
    assert access.wb_cabinet.shop_id == "123"
    assert access.tokens and len(access.tokens) > 0
    assert access.tokens[0].api_key == "test_key"