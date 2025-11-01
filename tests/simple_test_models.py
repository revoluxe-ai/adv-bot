"""
Простой тест для проверки моделей с использованием SQLAlchemy.
"""

import os

import pytest
from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.modules.common_slaves.wildberries.models import WBCabinet

# Создаем базу тестов
Base = declarative_base()
DB_PATH = "simple_test_db.sqlite"


# # Определяем модели для тестирования
# class WBCabinet(Base):
#     __tablename__ = "wbcabinet"
#     id = Column(Integer, primary_key=True)
#     balance = Column(Float, default=0, server_default=text("0"), nullable=False)
#     bonus = Column(Float, default=0, server_default=text("0"), nullable=False)
#     active = Column(Boolean, default=True)
#     shop_id = Column(String, nullable=False, unique=True)
#     balance_payments = relationship(
#         "WBBalancePayment", back_populates="wb_cabinet", uselist=True
#     )
#     bonus_payments = relationship(
#         "WBBonusPayment", back_populates="wb_cabinet", uselist=True
#     )

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     @property
#     def calculated_balance(self) -> float:
#         """Вычисляет баланс на основе начального значения balance и всех платежей"""
#         if not hasattr(self, "balance_payments") or not self.balance_payments:
#             return self.balance  # Возвращаем текущее значение, если нет платежей

#         # Суммируем все платежи и начальное значение баланса
#         return self.balance + sum(payment.amount for payment in self.balance_payments)

#     @property
#     def calculated_bonus(self):
#         """Вычисляет бонусы на основе начального значения bonus и всех платежей"""
#         if not hasattr(self, "bonus_payments") or not self.bonus_payments:
#             return self.bonus  # Возвращаем текущее значение, если нет платежей

#         # Суммируем все платежи и начальное значение бонусов
#         return self.bonus + sum(payment.amount for payment in self.bonus_payments)


class WBBalancePayment(Base):
    __tablename__ = "wb_balance_payment"
    id = Column(Integer, primary_key=True)
    wb_cabinet_id = Column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    wb_cabinet = relationship("WBCabinet", back_populates="balance_payments")


class WBBonusPayment(Base):
    __tablename__ = "wb_bonus_payment"
    id = Column(Integer, primary_key=True)
    wb_cabinet_id = Column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    wb_cabinet = relationship("WBCabinet", back_populates="bonus_payments")


# Создаем тестовую базу данных
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    # Создаем все таблицы
    Base.metadata.create_all(engine)

    # Создаем сессию
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()

    # Удаляем все таблицы
    Base.metadata.drop_all(engine)

    # Закрываем соединение с базой данных
    engine.dispose()

    # Удаляем файл базы данных
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except:
            pass


def test_wb_cabinet_calculated_balance(db_session):
    """Тестирование свойства calculated_balance"""

    # Создаем тестовый кабинет с начальным балансом
    cabinet = WBCabinet(shop_id="test_shop_1", balance=100.0)
    db_session.add(cabinet)
    db_session.commit()

    # Проверяем, что calculated_balance возвращает начальное значение баланса,
    # когда нет платежей
    assert cabinet.calculated_balance == 100.0

    # Добавляем платеж
    payment1 = WBBalancePayment(
        wb_cabinet_id=cabinet.id, amount=50.0, description="Test payment 1"
    )
    db_session.add(payment1)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_balance суммирует начальный баланс и платеж
    assert cabinet.calculated_balance == 150.0

    # Добавляем еще один платеж
    payment2 = WBBalancePayment(
        wb_cabinet_id=cabinet.id, amount=25.0, description="Test payment 2"
    )
    db_session.add(payment2)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_balance суммирует начальный баланс и все платежи
    assert cabinet.calculated_balance == 175.0

    # Добавляем отрицательный платеж (списание)
    payment3 = WBBalancePayment(
        wb_cabinet_id=cabinet.id, amount=-30.0, description="Test payment 3 (negative)"
    )
    db_session.add(payment3)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_balance правильно учитывает отрицательные платежи
    assert cabinet.calculated_balance == 145.0


def test_wb_cabinet_calculated_bonus(db_session):
    """Тестирование свойства calculated_bonus"""

    # Создаем тестовый кабинет с начальными бонусами
    cabinet = WBCabinet(shop_id="test_shop_2", bonus=50.0)
    db_session.add(cabinet)
    db_session.commit()

    # Проверяем, что calculated_bonus возвращает начальное значение бонусов,
    # когда нет транзакций
    assert cabinet.calculated_bonus == 50.0

    # Добавляем бонусную транзакцию
    bonus1 = WBBonusPayment(
        wb_cabinet_id=cabinet.id, amount=25.0, description="Test bonus 1"
    )
    db_session.add(bonus1)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_bonus суммирует начальные бонусы и транзакцию
    assert cabinet.calculated_bonus == 75.0

    # Добавляем еще одну бонусную транзакцию
    bonus2 = WBBonusPayment(
        wb_cabinet_id=cabinet.id, amount=10.0, description="Test bonus 2"
    )
    db_session.add(bonus2)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_bonus суммирует начальные бонусы и все транзакции
    assert cabinet.calculated_bonus == 85.0

    # Добавляем отрицательную бонусную транзакцию (списание)
    bonus3 = WBBonusPayment(
        wb_cabinet_id=cabinet.id, amount=-15.0, description="Test bonus 3 (negative)"
    )
    db_session.add(bonus3)
    db_session.commit()
    db_session.refresh(cabinet)

    # Проверяем, что calculated_bonus правильно учитывает отрицательные транзакции
    assert cabinet.calculated_bonus == 70.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
