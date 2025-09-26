from __future__ import annotations

from typing import Dict, Tuple

from app.core.mp.wb.adapters.base import BaseAdapter


class WbApiAdapterFactory:
    """Factory that creates and caches adapters per (shop_id, section, version)."""

    def __init__(self) -> None:
        self.adapters: Dict[Tuple[str, str, str], BaseAdapter] = {}

    def get_adapter(self, shop_id: str, section: str, version: str) -> BaseAdapter:
        key = (shop_id, section, version)
        if key in self.adapters:
            return self.adapters[key]
        # Concrete adapter creation is deferred; registry/conditional logic added later
        adapter = self._create_adapter(shop_id, section, version)
        self.adapters[key] = adapter
        return adapter

    def _create_adapter(self, shop_id: str, section: str, version: str) -> BaseAdapter:
        """Instantiate appropriate adapter class for section/version."""
        raise NotImplementedError
