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

## Учет списаний за рекламные кампании

Для учета списаний за рекламные кампании в системе реализован механизм двойной записи:

1. Создается запись в таблице `AdvPayment` с указанием даты и суммы списания
2. Создается соответствующая запись в таблице `WBBalancePayment` или `WBBonusPayment` (в зависимости от источника средств)

```python
# Пример учета списания за рекламную кампанию
# 1. Создание записи о платеже за рекламу
payment = AdvPayment(
    date=current_date,
    amount=price_for_adv,
    adv_setting_id=adv_setting.id
)
adv_setting.payments.append(payment)

# 2. Создание записи списания с баланса или бонусов
if calculated_bonus >= price_for_adv:
    # Списание с бонусов
    bonus_payment = WBBonusPayment(
        wb_cabinet_id=cabinet.id,
        amount=-price_for_adv,
        description=f"Списание за рекламную кампанию {adv_setting.adv_id}",
        operation_type="subtract"
    )
    session.add(bonus_payment)
    # НЕ обновляем прямое поле bonus, используем только транзакции
else:
    # Списание с баланса
    balance_payment = WBBalancePayment(
        wb_cabinet_id=cabinet.id,
        amount=-price_for_adv,
        description=f"Списание за рекламную кампанию {adv_setting.adv_id}"
    )
    session.add(balance_payment)
    # НЕ обновляем прямое поле balance, используем только транзакции
```

### Приоритеты списания

Система использует следующие приоритеты при списании:
1. Сначала всегда используются бонусы (`calculated_bonus`)
2. Если бонусов недостаточно, используется основной баланс (`calculated_balance`)
3. Если и баланса недостаточно, рекламная кампания деактивируется (устанавливается `bot_active = False`)

## Важные замечания

1. **Не модифицируйте напрямую** поля `balance` и `bonus` - это может привести к несогласованности данных.
2. Всегда проверяйте достаточность средств перед списанием: `if cabinet.calculated_balance >= amount`.
3. Для получения истории транзакций используйте запросы к таблицам `WBBalancePayment` и `WBBonusPayment`.
4. При работе с админ-панелью рекомендуется использовать функции из модуля `cabinet_bonus_manager`.
5. Всегда создавайте два типа записей при списании за рекламные кампании: в `AdvPayment` и в соответствующей таблице платежей.
6. Для расчета текущего баланса и бонусов всегда используйте гибридные свойства `calculated_balance` и `calculated_bonus`, которые учитывают все транзакции в системе.

## Использование в SQL-запросах

```python
from sqlalchemy import select, func
from app.modules.common_slaves.wildberries.models import WBCabinet

# Поиск кабинетов с балансом более 1000
query = select(WBCabinet).where(WBCabinet.calculated_balance > 1000)

# Агрегация по расчетным бонусам
query = select(func.sum(WBCabinet.calculated_bonus))
``` 