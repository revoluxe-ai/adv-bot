from __future__ import annotations

import logging

from app.core.mp.wb.protocols.base_wb_protocol import BaseWBAdapterProtocol
from app.core.mp.wb.token_management.factory import get_default_factory
from app.core.mp.wb.token_management.token_context import current_wb_access
from app.core.mp.wb.token_management.enhanced_factory import get_enhanced_factory
from app.core.mp.wb.token_management.enhanced_token_manager import (
    EnhancedShopTokenManager,
)

logger = logging.getLogger(__name__)


class BaseWBAdapter(BaseWBAdapterProtocol):
    """Базовый адаптер с общей логикой переключения токенов."""

    def __init__(
        self, http_client, wb_access=None, token_manager=None, use_enhanced: bool = True
    ):
        self.http_client = http_client
        self.wb_access = wb_access or current_wb_access.get()
        self.use_enhanced = use_enhanced

        if token_manager is not None:
            self._token_manager = token_manager
        elif use_enhanced:
            factory = get_enhanced_factory()
            self._token_manager = factory.get_or_create(self.wb_access)
        else:
            self._token_manager = get_default_factory().get_or_create(self.wb_access)

    @property
    def shop_id(self) -> str:
        return self._token_manager.shop_id

    async def set_next_token(self, method_name: str) -> None:
        """Пометить текущий токен как плохой для метода и переключиться."""
        if isinstance(self._token_manager, EnhancedShopTokenManager):
            current_token = await self._token_manager.get_best_token(method_name)
            if current_token:
                await self._token_manager.mark_token_bad(method_name, current_token.id)
        else:
            token = self._token_manager.current_token
            if not token:
                raise RuntimeError("No current token to mark bad")
            await self._token_manager.mark_token_bad(method_name, token.id)
