import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from tests.mocks import mock_metadata, MockWBCabinet, MockWBBalancePayment, MockWBBonusPayment

# Создаем тестовую базу данных в памяти
engine = create_engine('sqlite:///:memory:')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    # Создаем все таблицы
    mock_metadata.create_all(engine)
    
    # Создаем сессию
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
    
    # Удаляем все таблицы
    mock_metadata.drop_all(engine)


def test_wb_cabinet_calculated_balance(db_session: Session):
    """Тестирование гибридного свойства calculated_balance"""
    
    # Создаем тестовый кабинет с начальным балансом
    cabinet = MockWBCabinet(
        shop_id="test_shop_1",
        balance=100.0
    )
    db_session.add(cabinet)
    db_session.commit()
    
    # Проверяем, что calculated_balance возвращает начальное значение баланса,
    # когда нет платежей
    assert cabinet.calculated_balance == 100.0
    
    # Добавляем платеж
    payment1 = MockWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=50.0,
        description="Test payment 1"
    )
    db_session.add(payment1)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_balance суммирует начальный баланс и платеж
    assert cabinet.calculated_balance == 150.0
    
    # Добавляем еще один платеж
    payment2 = MockWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=25.0,
        description="Test payment 2"
    )
    db_session.add(payment2)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_balance суммирует начальный баланс и все платежи
    assert cabinet.calculated_balance == 175.0
    
    # Добавляем отрицательный платеж (списание)
    payment3 = MockWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=-30.0,
        description="Test payment 3 (negative)"
    )
    db_session.add(payment3)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_balance правильно учитывает отрицательные платежи
    assert cabinet.calculated_balance == 145.0


def test_wb_cabinet_calculated_bonus(db_session: Session):
    """Тестирование гибридного свойства calculated_bonus"""
    
    # Создаем тестовый кабинет с начальными бонусами
    cabinet = MockWBCabinet(
        shop_id="test_shop_2",
        bonus=50.0
    )
    db_session.add(cabinet)
    db_session.commit()
    
    # Проверяем, что calculated_bonus возвращает начальное значение бонусов,
    # когда нет транзакций
    assert cabinet.calculated_bonus == 50.0
    
    # Добавляем бонусную транзакцию
    bonus1 = MockWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=25.0,
        description="Test bonus 1"
    )
    db_session.add(bonus1)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_bonus суммирует начальные бонусы и транзакцию
    assert cabinet.calculated_bonus == 75.0
    
    # Добавляем еще одну бонусную транзакцию
    bonus2 = MockWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=10.0,
        description="Test bonus 2"
    )
    db_session.add(bonus2)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_bonus суммирует начальные бонусы и все транзакции
    assert cabinet.calculated_bonus == 85.0
    
    # Добавляем отрицательную бонусную транзакцию (списание)
    bonus3 = MockWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=-15.0,
        description="Test bonus 3 (negative)"
    )
    db_session.add(bonus3)
    db_session.commit()
    db_session.refresh(cabinet)
    
    # Проверяем, что calculated_bonus правильно учитывает отрицательные транзакции
    assert cabinet.calculated_bonus == 70.0 