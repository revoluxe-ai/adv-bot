from __future__ import annotations

from typing import Dict, Tuple

from app.core.mp.wb.adapters.base import BaseAdapter
from app.core.mp.wb.client_factory import ClientFactory
from app.core.mp.wb.rate_limit.storage import RateLimitStorage


class WbApiAdapterFactory:
    """Factory that creates and caches adapters per (shop_id, section, version)."""

    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory
        self._adapters_cache: Dict[Tuple[str, str, int], BaseAdapter] = {}

    def get_adapter(self, shop_id: str, section: str, version: int, rate_limit_storage: RateLimitStorage) -> BaseAdapter:
        key = (shop_id, section, version)
        if key in self._adapters_cache:
            return self._adapters_cache[key]
        
        adapter = self._get_new_adapter(shop_id, section, version, rate_limit_storage)
        self._adapters_cache[key] = adapter
        return adapter

    def _get_new_adapter(self, shop_id: str, section: str, version: int, rate_limit_storage: RateLimitStorage) -> BaseAdapter:
        client = self._client_factory.get_client(shop_id, section, version)

        if section == 'promotion':
            if version == 0:
                from .adapters.promotion.v0.adapter import PromotionAdapterV0
                return PromotionAdapterV0(shop_id, client, rate_limit_storage)
            elif version == 1:
                from .adapters.promotion.v1.adapter import PromotionAdapterV1
                return PromotionAdapterV1(shop_id, client, rate_limit_storage)
        raise ValueError(f"No adapter found for section '{section}' with version '{version}'")
