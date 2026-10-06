"""Структурные отказы MCP и OAuth. Данные магазина сюда не кладутся."""

from __future__ import annotations


class McpError(Exception):
    """Отказ протокола с машинным кодом и коротким сообщением.

    Attributes:
        code: Стабильный код (``UNAUTHENTICATED``, ``SHOP_NOT_GRANTED``, …).
        message: Короткий текст без секретов и без содержимого магазина.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class McpStorageError(McpError):
    """Redis или PostgreSQL недоступны. Вызывающий обязан fail-closed."""

    def __init__(self, message: str = "auth backend unavailable") -> None:
        super().__init__("AUTH_BACKEND_UNAVAILABLE", message)


class AuthorizationRedirectError(Exception):
    """Ошибка ``/oauth/authorize``, которую можно вернуть клиенту редиректом.

    Создаётся только после того, как ``client_id`` и ``redirect_uri`` уже
    проверены и принадлежат друг другу. До этой проверки отказ остаётся
    локальным HTTP-ответом и не уходит на произвольный адрес.
    """

    def __init__(self, location: str) -> None:
        super().__init__("authorization redirect")
        self.location = location
