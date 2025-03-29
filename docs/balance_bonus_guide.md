# Руководство по работе с балансом и бонусами

## Общая концепция

В системе реализована гибридная модель учета баланса и бонусов, которая объединяет:
1. Исторические данные из полей `balance` и `bonus` в таблице `WBCabinet`
2. Записи транзакций в таблицах `WBBalancePayment` и `WBBonusPayment`

Основной принцип: **расчетные значения = исходные поля + сумма всех транзакций**.

## Гибридные свойства

Модель `WBCabinet` предоставляет два гибридных свойства:
- `calculated_balance` - расчетный баланс (исходное значение баланса + сумма всех платежей)
- `calculated_bonus` - расчетные бонусы (исходное значение бонусов + сумма всех бонусных транзакций)

Эти свойства можно использовать как в Python-коде, так и в SQL-запросах.

## Как правильно работать с балансом и бонусами

### Получение значений
```python
# Получение расчетного баланса
balance = cabinet.calculated_balance

# Получение расчетных бонусов
bonus = cabinet.calculated_bonus
```

### Изменение баланса
```python
# Добавление средств
balance_payment = WBBalancePayment(
    wb_cabinet_id=cabinet.id,
    amount=amount,  # Положительное число для пополнения
    description="Описание транзакции"
)
session.add(balance_payment)

# Списание средств
balance_payment = WBBalancePayment(
    wb_cabinet_id=cabinet.id,
    amount=-amount,  # Отрицательное число для списания
    description="Описание списания"
)
session.add(balance_payment)
```

### Изменение бонусов
```python
# Начисление бонусов
bonus_payment = WBBonusPayment(
    wb_cabinet_id=cabinet.id,
    amount=amount,  # Положительное число для начисления
    description="Описание начисления",
    operation_type="add"  # Тип операции (для админов)
)
session.add(bonus_payment)

# Списание бонусов
bonus_payment = WBBonusPayment(
    wb_cabinet_id=cabinet.id,
    amount=-amount,  # Отрицательное число для списания
    description="Описание списания",
    operation_type="subtract"  # Тип операции (для админов)
)
session.add(bonus_payment)
```

### Администраторские операции с бонусами

Для администраторов существуют специальные поля в таблице `WBBonusPayment`:
- `operation_type` - тип операции ('add', 'subtract', 'reset')
- `admin_user_id` - ID администратора, выполнившего операцию

```python
# Пример админской операции
bonus_payment = WBBonusPayment(
    wb_cabinet_id=cabinet.id,
    amount=amount,
    description="Описание операции",
    operation_type="add",
    admin_user_id=admin_id
)
session.add(bonus_payment)
```

## Важные замечания

1. **Не модифицируйте напрямую** поля `balance` и `bonus` - это может привести к несогласованности данных.
2. Всегда проверяйте достаточность средств перед списанием: `if cabinet.calculated_balance >= amount`.
3. Для получения истории транзакций используйте запросы к таблицам `WBBalancePayment` и `WBBonusPayment`.
4. При работе с админ-панелью рекомендуется использовать функции из модуля `cabinet_bonus_manager`.

## Использование в SQL-запросах

```python
from sqlalchemy import select, func
from app.modules.common_slaves.wildberries.models import WBCabinet

# Поиск кабинетов с балансом более 1000
query = select(WBCabinet).where(WBCabinet.calculated_balance > 1000)

# Агрегация по расчетным бонусам
query = select(func.sum(WBCabinet.calculated_bonus))
``` 