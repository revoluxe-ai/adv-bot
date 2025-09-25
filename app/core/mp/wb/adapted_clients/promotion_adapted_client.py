from typing import Any

import httpx

from ..generated.promotion.v1.client.client import AuthenticatedClient


class AdaptedClient(AuthenticatedClient):
    def __init__(self, httpx_client: httpx.AsyncClient | None, token: str, *, base_url: str = ""):
        # Инициализируем базовый AuthenticatedClient, передавая минимально необходимые поля
        super().__init__(
            base_url=base_url or (httpx_client.base_url if httpx_client else ""),
            cookies={},
            headers={},
            timeout=None,
            verify_ssl=True,
            follow_redirects=False,
            httpx_args={},
            token=token,
        )
        # Если нам передали внешний httpx.AsyncClient — используем его
        if httpx_client is not None:
            self.set_async_httpx_client(httpx_client)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        # Прокси-запрос через асинхронный клиент, настроенный в AuthenticatedClient
        client = self.get_async_httpx_client()
        return await client.request(method=method, url=url, **kwargs)
