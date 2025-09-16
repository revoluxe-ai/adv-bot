class BalanceManagerError(Exception):
    """Базовое исключение для модуля управления балансом"""

    pass


class UserNotFoundError(BalanceManagerError):
    """Пользователь не найден"""

    pass


class CabinetNotFoundError(BalanceManagerError):
    """Кабинет WB не найден"""

    pass


class PaymentNotFoundError(BalanceManagerError):
    """Платеж не найден"""

    pass


class InsufficientBalanceError(BalanceManagerError):
    """Недостаточно средств на балансе"""

    pass


class InvalidAmountError(BalanceManagerError):
    """Некорректная сумма платежа"""

    pass
