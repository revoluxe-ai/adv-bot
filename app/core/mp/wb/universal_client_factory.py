import typing

from app.core.mp.wb.exceptions import ApiForbiddenError
from app.core.mp.wb.mixins.set_httpx_session_and_headers_mixin import SetHttpxSessionAndHeadersMixin


class UniversalClientFactory:
    """
    Универсальная фабрика клиентов для разных разделов.
    Принимает client_class, контейнер раздела, менеджер токенов, функцию получения токенов, section.
    Возвращает клиента с нужным токеном и сессией.
    """

    def __init__(
            self,
            client_class: type,
            di_container,
            token_manager,
            fetch_tokens_func: typing.Callable[[str], typing.Awaitable[typing.List]],
            section: str,
            token_id_getter: typing.Callable = lambda t: t,
    ):
        self._client_class = client_class
        self._di_container = di_container
        self._token_manager = token_manager
        self._fetch_tokens_func = fetch_tokens_func
        self._section = section
        self._token_id_getter = token_id_getter

    async def get_client(self, shop_id: str) -> typing.Any:
        token = await self._token_manager.get_token(
            self._section, shop_id, self._fetch_tokens_func
        )
        if not token:
            raise ApiForbiddenError(f"Нет валидных токенов для магазина {shop_id} ({self._section})")
        async_client = self._di_container.httpx_async_client()

        # Создаём класс-наследник с миксином
        class AdaptedClient(self._client_class, SetHttpxSessionAndHeadersMixin):
            pass

        client = AdaptedClient(token=token.api_key)
        client.set_async_httpx_client(async_client)
        if hasattr(client, 'set_token_invalid_callback'):
            async def mark_invalid():
                await self.mark_token_invalid(shop_id, token)

            client.set_token_invalid_callback(mark_invalid)
        return client

    async def mark_token_invalid(self, shop_id: str, token):
        await self._token_manager.mark_token_invalid(
            self._section, shop_id, token, self._token_id_getter
        )

    async def refresh_tokens(self, shop_id: str):
        await self._token_manager.refresh_tokens(
            self._section, shop_id, self._fetch_tokens_func
        )
