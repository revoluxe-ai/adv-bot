from __future__ import annotations

import httpx
from typing import Callable, Awaitable, Optional, Any, Dict


class HTTPXClientWrapper:
    def __init__(
        self,
        client: httpx.AsyncClient,
        auth_header_name: str,
        token_prefix: str,
        get_token_cb: Callable[[], Awaitable[str]],
        mark_token_invalid_cb: Callable[[Optional[str]], Awaitable[None]],
    ):
        self._client = client
        self._auth_header_name = auth_header_name
        self._token_prefix = token_prefix
        self._get_token_cb = get_token_cb
        self._mark_token_invalid_cb = mark_token_invalid_cb

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        _headers = kwargs.pop("headers", {}) or {}

        # 1. Получаем актуальный токен
        token = await self._get_token_cb()
        _headers[self._auth_header_name] = f"{self._token_prefix}{token}".strip()
        kwargs["headers"] = _headers

        # 2. Отправляем запрос
        response = await self._client.request(method, url, **kwargs)

        # 3. Обрабатываем 401 Unauthorized
        if response.status_code == 401:
            # Помечаем текущий токен как невалидный
            await self._mark_token_invalid_cb(token)
            # В данном случае, просто возвращаем 401. Декоратор retry_decorator может его перехватить.

        return response

    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)
