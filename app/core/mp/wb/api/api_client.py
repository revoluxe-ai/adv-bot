# app/core/mp/wb/api_client.py
from typing import Any
import logging

import httpx
from attrs import define, field

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum

logger = logging.getLogger(__name__)


class _AuthAsyncProxy:
    """Тонкий прокси над общим httpx.AsyncClient: добавляет Authorization и НЕ закрывает клиент."""

    def __init__(self, httpx_client: httpx.AsyncClient, token: str) -> None:
        self._httpx_client = httpx_client
        self._token = token
        self._header_name = "Authorization"
        self._prefix = "Bearer"

    async def __aenter__(self):
        # Ничего не открываем: клиент управляется извне (singletons per section)
        return self

    async def __aexit__(self, exc_type: str, exc: Exception, tb: str) -> bool:
        # И ничего не закрываем
        return False

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.get("headers") or {})
        headers[self._header_name] = f"{self._prefix} {self._token}"
        kwargs["headers"] = headers
        return await self._httpx_client.request(method=method, url=url, **kwargs)


@define
class AuthenticatedCastClient:
    """Удовлетворяет ожиданиям сгенерённого кода, но подкидывает наш proxy вместо нового клиента."""

    _base_url: str = field(alias="base_url")
    _httpx_client: httpx.AsyncClient = field(alias="httpx_client")
    _token: str = field(alias="token")
    _section: SectionsEnum = field(alias="section")
    # генератор часто читает этот флаг
    raise_on_unexpected_status: bool = field(default=False)

    @property
    def section(self) -> SectionsEnum:
        return self._section

    @property
    def token_hash(self) -> str:
        from .token_hash import get_token_hash

        return get_token_hash(self._token)

    @staticmethod
    # иногда генератор спрашивает базовые заголовки
    def get_headers() -> dict[str, str]:
        # Можно вернуть пусто — токен подмешает proxy непосредственно в запросе
        return {}

    def get_async_httpx_client(self) -> _AuthAsyncProxy:
        return _AuthAsyncProxy(self._httpx_client, self._token)
