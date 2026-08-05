"""Создание shared httpx.AsyncClient для секций WB API.

Модуль централизует параметры connection pool/timeout и логирует создание
клиентов, чтобы диагностировать утечки отдельных PROMOTION pools.
"""

import logging
from typing import Self

import httpx

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum

logger = logging.getLogger(__name__)

HTTPX_CONNECT_TIMEOUT_SEC = 10.0
HTTPX_READ_TIMEOUT_SEC = 30.0
HTTPX_WRITE_TIMEOUT_SEC = 10.0
HTTPX_POOL_TIMEOUT_SEC = 60.0
HTTPX_MAX_CONNECTIONS = 200
HTTPX_MAX_KEEPALIVE_CONNECTIONS = 50


class HttpxClientHandler:
    """Фабрика shared httpx.AsyncClient по WB API section."""

    _BASE_URLS: dict[SectionsEnum, str] = {
        SectionsEnum.ANALYTIC_AND_DATA: "https://seller-analytics-api.wildberries.ru",
        SectionsEnum.PROMOTION: "https://advert-api.wildberries.ru",
        SectionsEnum.CONTENT: "https://content-api.wildberries.ru",
        SectionsEnum.STATISTICS: "https://statistics-api.wildberries.ru",
    }

    def __init__(self):
        self._httpx_clients: dict[SectionsEnum, httpx.AsyncClient] = {}
        logger.info(
            "event=httpx_client_handler_created handler_id=%s caller=%s",
            id(self),
            "HttpxClientHandler.__init__",
        )

    async def init(self) -> Self:
        """Вернуть инициализированный handler без побочных эффектов."""
        return self

    def get_httpx_client(self, section: SectionsEnum) -> httpx.AsyncClient:
        """Вернуть shared AsyncClient для section, создав его при первом обращении."""
        if section not in self._httpx_clients:
            base_url = self._BASE_URLS.get(section)
            if base_url is None:
                raise ValueError(f"Base URL for section {section} is not configured")

            # глобальный клиент
            timeout = httpx.Timeout(
                connect=HTTPX_CONNECT_TIMEOUT_SEC,
                read=HTTPX_READ_TIMEOUT_SEC,
                write=HTTPX_WRITE_TIMEOUT_SEC,
                pool=HTTPX_POOL_TIMEOUT_SEC,
            )
            limits = httpx.Limits(
                max_connections=HTTPX_MAX_CONNECTIONS,
                max_keepalive_connections=HTTPX_MAX_KEEPALIVE_CONNECTIONS,
            )

            client = httpx.AsyncClient(
                base_url=base_url, timeout=timeout, limits=limits
            )
            logger.info(
                "event=httpx_async_client_created "
                "handler_id=%s async_client_id=%s section=%s shop_id=%s "
                "max_connections=%s max_keepalive_connections=%s "
                "pool_timeout_sec=%.1f connect_timeout_sec=%.1f "
                "read_timeout_sec=%.1f write_timeout_sec=%.1f",
                id(self),
                id(client),
                section.name,
                "—",
                HTTPX_MAX_CONNECTIONS,
                HTTPX_MAX_KEEPALIVE_CONNECTIONS,
                HTTPX_POOL_TIMEOUT_SEC,
                HTTPX_CONNECT_TIMEOUT_SEC,
                HTTPX_READ_TIMEOUT_SEC,
                HTTPX_WRITE_TIMEOUT_SEC,
            )

            self._httpx_clients[section] = client

        return self._httpx_clients[section]

    async def aclose(self):
        """Закрыть все созданные AsyncClient и очистить registry."""
        for section, client in self._httpx_clients.items():
            logger.info(
                "event=httpx_async_client_closed "
                "handler_id=%s async_client_id=%s section=%s shop_id=%s",
                id(self),
                id(client),
                section.name,
                "—",
            )
            await client.aclose()
        self._httpx_clients.clear()
        logger.info("event=httpx_client_handler_closed handler_id=%s", id(self))

    async def shutdown(self):
        """Alias для graceful shutdown handler-а."""
        await self.aclose()
