# app/core/mp/wb/api_client.py
"""Authenticated httpx proxy для сгенерированных WB API clients."""

import asyncio
import time
from typing import Any
import logging

import httpx
from attrs import define, field

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.promotion_http_concurrency import (
    WAIT_WARN_SEC,
    acquire_promotion_http,
)

logger = logging.getLogger(__name__)


class _AuthAsyncProxy:
    """Тонкий прокси над общим httpx.AsyncClient: добавляет Authorization и НЕ закрывает клиент."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        token: str,
        *,
        section: SectionsEnum,
        shop_id: str | None = None,
    ) -> None:
        self._httpx_client = httpx_client
        self._token = token
        self._section = section
        self._shop_id = shop_id
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
        if self._section is SectionsEnum.PROMOTION:
            total_started = time.monotonic()
            async with acquire_promotion_http(
                shop_id=self._shop_id,
                http_method=method,
                endpoint=url,
            ) as timing:
                request_started = time.monotonic()
                try:
                    response = await self._httpx_client.request(
                        method=method, url=url, **kwargs
                    )
                except Exception as exc:
                    inside_sec = time.monotonic() - request_started
                    total_sec = time.monotonic() - total_started
                    self._log_promotion_request_timing(
                        method=method,
                        url=url,
                        wait_semaphore_sec=timing.wait_semaphore_sec,
                        inside_request_duration_sec=inside_sec,
                        total_duration_sec=total_sec,
                        in_flight=timing.in_flight,
                        limit=timing.limit,
                        success=False,
                        exc=exc,
                    )
                    raise

                inside_sec = time.monotonic() - request_started
                total_sec = time.monotonic() - total_started
                self._log_promotion_request_timing(
                    method=method,
                    url=url,
                    wait_semaphore_sec=timing.wait_semaphore_sec,
                    inside_request_duration_sec=inside_sec,
                    total_duration_sec=total_sec,
                    in_flight=timing.in_flight,
                    limit=timing.limit,
                    success=True,
                    exc=None,
                )
                return response
        return await self._httpx_client.request(method=method, url=url, **kwargs)

    def _log_promotion_request_timing(
        self,
        *,
        method: str,
        url: str,
        wait_semaphore_sec: float,
        inside_request_duration_sec: float,
        total_duration_sec: float,
        in_flight: int,
        limit: int,
        success: bool,
        exc: Exception | None,
    ) -> None:
        """Логировать только диагностически значимые PROMOTION HTTP timings."""
        pool_timeout = _is_pool_timeout(exc)
        should_warn = (
            wait_semaphore_sec > WAIT_WARN_SEC
            or total_duration_sec > 10.0
            or pool_timeout
            or exc is not None
        )
        if not should_warn:
            return

        logger.warning(
            "wb_promotion_http_timing "
            "shop_id=%s endpoint=%s coroutine=%s section=%s "
            "wait_semaphore_sec=%.3f inside_request_duration_sec=%.3f "
            "total_duration_sec=%.3f success=%s exception_type=%s "
            "pool_timeout=%s in_flight=%s limit=%s "
            "httpx_client_id=%s",
            self._shop_id or "—",
            _format_endpoint(method, url),
            _current_task_name(),
            self._section.name,
            wait_semaphore_sec,
            inside_request_duration_sec,
            total_duration_sec,
            success,
            type(exc).__name__ if exc is not None else "—",
            pool_timeout,
            in_flight,
            limit,
            id(self._httpx_client),
        )


@define
class AuthenticatedCastClient:
    """Удовлетворяет ожиданиям сгенерённого кода, но подкидывает наш proxy вместо нового клиента."""

    _base_url: str = field(alias="base_url")
    _httpx_client: httpx.AsyncClient = field(alias="httpx_client")
    _token: str = field(alias="token")
    _section: SectionsEnum = field(alias="section")
    _shop_id: str | None = field(default=None, alias="shop_id")
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
        return _AuthAsyncProxy(
            self._httpx_client,
            self._token,
            section=self._section,
            shop_id=self._shop_id,
        )


def _is_pool_timeout(exc: Exception | None) -> bool:
    """Определить raw httpx/httpcore PoolTimeout на уровне proxy."""
    if exc is None:
        return False
    return isinstance(exc, httpx.PoolTimeout) or type(exc).__name__ == "PoolTimeout"


def _format_endpoint(method: str, url: str) -> str:
    """Сформировать endpoint для диагностических логов PROMOTION."""
    return f"{method} {url}"


def _current_task_name() -> str:
    """Вернуть имя текущей asyncio task как caller/coroutine, если оно задано."""
    task = asyncio.current_task()
    if task is None:
        return "—"
    return task.get_name()
