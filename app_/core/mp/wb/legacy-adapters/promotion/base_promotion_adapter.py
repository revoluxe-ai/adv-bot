"""Базовый адаптер для Promotion API с общей логикой."""

import logging
from typing import Any

from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.shared.domain.protocols.wb_token import WBTokenProtocol
from ..base_adapter import BaseAPIAdapter

logger = logging.getLogger(__name__)


class BasePromotionAdapter(BaseAPIAdapter):
    """Базовый адаптер для всех версий Promotion API."""

    def __init__(self, http_client, wb_access: WBCabinetAccess, **kwargs):
        super().__init__(
            http_client=http_client,
            wb_access=wb_access,
            api_service="promotion",
            **kwargs,
        )

    def _create_generated_client(self, token: WBTokenProtocol) -> Any:
        """Создать generated клиент для Promotion API."""
        try:
            from ...api_client.clients.promotion.generated.v1.marketing_i_prodvizhenie.client import (
                AuthenticatedClient,
            )
            from ...utils.host_utils import resolve_wb_base_url

            base_url = resolve_wb_base_url("promotion")
            logger.info(f"🔍 WB Promotion base_url resolved: '{base_url}'")

            assert base_url and base_url.startswith(
                "http"
            ), f"❌ Invalid base_url: '{base_url}'"

            token_value = token.api_key
            generated_client = AuthenticatedClient(base_url=base_url, token=token_value)

            # Создаем кастомный httpx клиент с авторизацией
            custom_client = self._create_http_client_with_auth(base_url, token_value)
            generated_client.set_async_httpx_client(custom_client)

            logger.info(f"🔍 Created Promotion client for token {token_value[:20]}...")
            return generated_client

        except Exception:
            logger.exception("Failed to create generated client for Promotion API")
            raise
