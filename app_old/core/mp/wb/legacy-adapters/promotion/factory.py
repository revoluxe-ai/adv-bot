"""Фабрика адаптеров для Promotion API."""
from typing import Any

import httpx

from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess


def create_promotion_adapter(
    version: str,
    wb_access: WBCabinetAccess,
    http_client: httpx.AsyncClient
) -> Any:
    """
    Создать адаптер для Promotion API указанной версии.
    
    Args:
        version: Версия API ("v1", "v2", etc.)
        wb_access: Объект доступа к WB API
        http_client: HTTP клиент (Singleton)
        
    Returns:
        Экземпляр адаптера для указанной версии
        
    Raises:
        ValueError: Если версия не поддерживается
    """
    if version == "v1":
        from .v1_adapter import PromotionV1Adapter
        return PromotionV1Adapter(http_client, wb_access)
    elif version == "v2":
        # Будущая версия
        from .v2_adapter import PromotionV2Adapter
        return PromotionV2Adapter(http_client, wb_access)
    else:
        raise ValueError(f"Unsupported promotion API version: {version}")
