import pytest

class SimpleWBCabinet:
    def __init__(self, shop_id, balance=0.0, bonus=0.0):
        self.id = 1
        self.shop_id = shop_id
        self.balance = balance
        self.bonus = bonus
        self.balance_payments = []
        self.bonus_payments = []

    @property
    def calculated_balance(self):
        """Вычисляет баланс на основе начального значения balance и всех платежей"""
        if not self.balance_payments:
            return self.balance  # Возвращаем текущее значение, если нет платежей
        
        # Суммируем все платежи и начальное значение баланса
        return self.balance + sum(payment.amount for payment in self.balance_payments)
    
    @property
    def calculated_bonus(self):
        """Вычисляет бонусы на основе начального значения bonus и всех платежей"""
        if not self.bonus_payments:
            return self.bonus  # Возвращаем текущее значение, если нет платежей
        
        # Суммируем все платежи и начальное значение бонусов
        return self.bonus + sum(payment.amount for payment in self.bonus_payments)

class SimpleWBBalancePayment:
    def __init__(self, wb_cabinet_id, amount, description):
        self.id = 1
        self.wb_cabinet_id = wb_cabinet_id
        self.amount = amount
        self.description = description

class SimpleWBBonusPayment:
    def __init__(self, wb_cabinet_id, amount, description):
        self.id = 1
        self.wb_cabinet_id = wb_cabinet_id
        self.amount = amount
        self.description = description

@pytest.mark.asyncio
async def test_wb_cabinet_calculated_balance():
    """Тестирование гибридного свойства calculated_balance"""
    
    # Создаем тестовый кабинет с начальным балансом
    cabinet = SimpleWBCabinet(
        shop_id="test_shop_1",
        balance=100.0
    )
    
    # Проверяем, что calculated_balance возвращает начальное значение баланса,
    # когда нет платежей
    assert cabinet.calculated_balance == 100.0
    
    # Добавляем платеж
    payment1 = SimpleWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=50.0,
        description="Test payment 1"
    )
    cabinet.balance_payments = [payment1]
    
    # Проверяем, что calculated_balance суммирует начальный баланс и платеж
    assert cabinet.calculated_balance == 150.0
    
    # Добавляем еще один платеж
    payment2 = SimpleWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=25.0,
        description="Test payment 2"
    )
    cabinet.balance_payments = [payment1, payment2]
    
    # Проверяем, что calculated_balance суммирует начальный баланс и все платежи
    assert cabinet.calculated_balance == 175.0
    
    # Добавляем отрицательный платеж (списание)
    payment3 = SimpleWBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=-30.0,
        description="Test payment 3 (negative)"
    )
    cabinet.balance_payments = [payment1, payment2, payment3]
    
    # Проверяем, что calculated_balance правильно учитывает отрицательные платежи
    assert cabinet.calculated_balance == 145.0


@pytest.mark.asyncio
async def test_wb_cabinet_calculated_bonus():
    """Тестирование гибридного свойства calculated_bonus"""
    
    # Создаем тестовый кабинет с начальными бонусами
    cabinet = SimpleWBCabinet(
        shop_id="test_shop_2",
        bonus=50.0
    )
    
    # Проверяем, что calculated_bonus возвращает начальное значение бонусов,
    # когда нет транзакций
    assert cabinet.calculated_bonus == 50.0
    
    # Добавляем бонусную транзакцию
    bonus1 = SimpleWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=25.0,
        description="Test bonus 1"
    )
    cabinet.bonus_payments = [bonus1]
    
    # Проверяем, что calculated_bonus суммирует начальные бонусы и транзакцию
    assert cabinet.calculated_bonus == 75.0
    
    # Добавляем еще одну бонусную транзакцию
    bonus2 = SimpleWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=10.0,
        description="Test bonus 2"
    )
    cabinet.bonus_payments = [bonus1, bonus2]
    
    # Проверяем, что calculated_bonus суммирует начальные бонусы и все транзакции
    assert cabinet.calculated_bonus == 85.0
    
    # Добавляем отрицательную бонусную транзакцию (списание)
    bonus3 = SimpleWBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=-15.0,
        description="Test bonus 3 (negative)"
    )
    cabinet.bonus_payments = [bonus1, bonus2, bonus3]
    
    # Проверяем, что calculated_bonus правильно учитывает отрицательные транзакции
    assert cabinet.calculated_bonus == 70.0 