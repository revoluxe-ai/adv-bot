from __future__ import annotations

from typing import Dict, Tuple

from app.core.mp.wb.adapters.base import BaseAdapter


class WbApiAdapterFactory:
    """Factory that creates and caches adapters per (shop_id, section, version)."""

    def __init__(self) -> None:
        self._adapters_cache: Dict[Tuple[str, str, str], BaseAdapter] = {}

    def get_adapter(self, shop_id: str, section: str, version: str) -> BaseAdapter:
        key = (shop_id, section, version)
        if key in self._adapters_cache:
            return self._adapters_cache[key]
        # Concrete adapter creation is deferred; registry/conditional logic added later
        adapter = self._create_adapter(shop_id, section, version)
        self._adapters_cache[key] = adapter
        return adapter

    def _create_adapter(self, shop_id: str, section: str, version: str) -> BaseAdapter:
        key = (shop_id, section, version)
        if not key in self._adapters_cache:
            self._adapters_cache[key] = self._get_new_adapter(shop_id, section, version)
        return self._adapters_cache[key]

    def _get_new_adapter(self, shop_id: str, section: str, version: str) -> BaseAdapter:
        if section == 'promotion' and version == 'v1':
            from .adapters.promotion.v1.adapter import PromotionAdapterV1
            return PromotionAdapterV1(shop_id)
        raise ValueError(f"No adapter found for section '{section}' with version '{version}'")
