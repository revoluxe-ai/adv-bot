"""Factory WBManagerHub с ContextVar binding для shop-контекста.

Диагностические логи creation-path помогают отличить один штатный shared
HttpxClientHandler от fallback/leak клиентов внутри отдельных задач.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from app.core.di.client_di.wb_manager_hub_container import WBManagerHubContainer
from app.core.di.wb_manager_hub.wb_manager_hub import WBManagerHub
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient

logger = logging.getLogger(__name__)


class WBManagerHubFactory:
    """Создаёт WBManagerHub per shop и кладёт его в ContextVar."""

    _wb_manager_hub_context_var: ContextVar[WBManagerHub | None] = ContextVar(
        "wb_manager_hub_context", default=None
    )

    def __init__(
        self,
        httpx_client_handler: HttpxClientHandler,
        redis_client_wrapper: RedisClient,
    ):
        self.__httpx_client_handler = httpx_client_handler
        self.__redis_client_wrapper = redis_client_wrapper
        self.__object_collection: dict[str, WBManagerHub] = {}
        self._tokens: dict[str, Token[WBManagerHub | None]] = {}

    def set_wb_manager_hub(self, shop_id: str) -> None:
        """Создать hub для shop при первом обращении и установить его в ContextVar."""
        if shop_id not in self.__object_collection:
            wb_manager_hub_container: WBManagerHubContainer = WBManagerHubContainer(
                _shop_id=shop_id,
                _httpx_client_handler=self.__httpx_client_handler,
                _redis_wrapper=self.__redis_client_wrapper,
            )
            logger.info(
                "event=wb_manager_hub_container_created shop_id=%s "
                "handler_id=%s caller=%s fallback=%s",
                shop_id,
                id(self.__httpx_client_handler),
                "WBManagerHubFactory.set_wb_manager_hub",
                False,
            )
            wb_manager_hub: WBManagerHub = wb_manager_hub_container.wb_manager_hub()
            self.__object_collection[shop_id] = wb_manager_hub
            self._set_manager_in_context(shop_id, wb_manager_hub)
        return None

    def get_wb_manager_hub(self, shop_id: str) -> WBManagerHub:
        """Вернуть WBManagerHub для shop, создав штатный singleton при необходимости."""
        self.set_wb_manager_hub(shop_id)
        return self.__object_collection[shop_id]

    def _set_manager_in_context(
        self, shop_id: str, wb_manager_hub: WBManagerHub
    ) -> None:
        token = self._wb_manager_hub_context_var.set(wb_manager_hub)
        self._tokens[shop_id] = token

    def reset_shop(self, shop_id: str) -> None:
        """Сбросить ContextVar token и удалить hub для shop."""
        self._wb_manager_hub_context_var.reset(self._tokens[shop_id])
        del self.__object_collection[shop_id]

    @classmethod
    def get_wb_manager_from_context(cls) -> WBManagerHub:
        """Получить WBManagerHub из текущего ContextVar или бросить ошибку."""
        hub: WBManagerHub | None = cls._wb_manager_hub_context_var.get()
        if hub is None:
            raise RuntimeError("WB manager hub not set")
        return hub

    @classmethod
    @contextmanager
    def bind_hub_in_context(cls, hub: WBManagerHub) -> Generator[None, None, None]:
        """Временно установить hub в ContextVar (snapshot warmup вне shop-runner)."""
        token = cls._wb_manager_hub_context_var.set(hub)
        try:
            yield
        finally:
            cls._wb_manager_hub_context_var.reset(token)
