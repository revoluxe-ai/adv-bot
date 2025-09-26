from typing import Optional, Callable, Awaitable
import asyncio
import httpx
from app.core.mp.wb.adapters.httpx_client_wrapper import HTTPXClientWrapper # Не использовать напрямую, только для подсказки типов


class AdapterAuthClient:
    """Миксин для управления токенами и HTTP-клиентами в сгенерированных клиентах.
    Предназначен для смешивания с generated `AuthenticatedClient` классами.
    """

    def __init__(self) -> None:
        # Эти атрибуты будут установлены ClientFactory
        self._async_client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._prefix: Optional[str] = None # Изменение: _prefix вместо self.prefix
        self._token_invalid_cb: Optional[Callable[[Optional[str]], Awaitable[None]]] = None
        # Имя заголовка авторизации и префикс токена будут предоставлены сгенерированным клиентом
        self.auth_header_name: str = "Authorization"
        self.prefix: str = "" # Изменение: это не нужно, если используем _prefix

    def with_headers(self, headers: dict[str, str]) -> None:
        raise RuntimeError('Управление заголовками осуществляется через set_token')

    def with_cookies(self, cookies: dict[str, str]) -> None:
        raise RuntimeError('Управление cookies не поддерживается напрямую этим миксином')

    def with_timeout(self, timeout: httpx.Timeout) -> None:
        raise RuntimeError('Управление таймаутом осуществляется через конфигурацию httpx.AsyncClient')

    def set_async_httpx_client(self, async_client: httpx.AsyncClient) -> "AdapterAuthClient":
        """Привязать shared AsyncClient к этому адаптированному клиенту."""
        self._async_client = async_client
        return self

    def set_token(self, token: str, prefix: Optional[str] = None) -> "AdapterAuthClient":
        """Установить/заменить токен авторизации для этого клиента и обновить заголовки.
        
        Если `prefix` указан, он будет использован как префикс для токена (например, "Bearer").
        """
        self._token = token
        if prefix is not None:
            self._prefix = prefix # Изменение: устанавливаем _prefix
        
        auth_value = f"{self._prefix or '''} {self._token}".strip() # Изменение: используем _prefix
        
        # Обновляем заголовки сгенерированного клиента (если он их имеет)
        if hasattr(self, '_headers') and getattr(self, 'auth_header_name', None):
            self._headers[self.auth_header_name] = auth_value
        
        # Обновляем заголовки async клиента (если он привязан)
        if self._async_client is not None and hasattr(self._async_client, 'headers'):
            self._async_client.headers[self.auth_header_name] = auth_value

        return self

    def set_token_invalid_callback(self, cb: Callable[[Optional[str]], Awaitable[None]]) -> None:
        """Зарегистрировать асинхронный callback для обработки невалидных токенов."""
        self._token_invalid_cb = cb

    def mark_token_invalid(self, token: Optional[str] = None) -> None:
        """Вызвать callback для невалидного токена (асинхронно через задачу).
        
        Если callback является корутиной и есть запущенный цикл событий, то он будет
        запланирован как задача. В противном случае, будет выполнен синхронно.
        Ошибки в callback игнорируются.
        """
        if self._token_invalid_cb is None:
            return
            
        try:
            result = self._token_invalid_cb(token)
            if hasattr(result, '__await__'): # Проверяем, является ли результат корутиной
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(result) # Планируем как задачу
                except RuntimeError:
                    asyncio.run(result) # Выполняем синхронно, если нет запущенного цикла
        except Exception:
            pass # Игнорируем все исключения в callback
