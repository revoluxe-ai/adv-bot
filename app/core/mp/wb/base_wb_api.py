from __future__ import annotations

from typing import ClassVar

from app.core.mp.wb.adapter_factory import WbApiAdapterFactory
from app.core.mp.wb.adapters.base import BaseAdapter
from app.core.mp.wb.rate_limit.storage import RateLimitStorage


class BaseWBApi:
    """Core helper that delivers WB API adapters scoped by shop/section/version."""

    def __init__(self, shop_id: str, adapter_factory: WbApiAdapterFactory, rate_limit_storage: RateLimitStorage) -> None:
        self.shop_id = shop_id
        self.adapter_factory = adapter_factory
        self.rate_limit_storage = rate_limit_storage

    def get_adapter(self, section: str, version: int) -> BaseAdapter:
        """Return adapter instance cached per (shop, section, version)."""
        return self.adapter_factory.get_adapter(self.shop_id, section, version, self.rate_limit_storage)



