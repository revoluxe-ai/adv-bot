from __future__ import annotations

from typing import ClassVar

from app.core.mp.wb.adapter_factory import WbApiAdapterFactory
from app.core.mp.wb.adapters.base import BaseAdapter


class BaseWBApi:
    """Core helper that delivers WB API adapters scoped by shop/section/version."""

    adapter_factory: ClassVar[WbApiAdapterFactory] = WbApiAdapterFactory()

    def __init__(self, shop_id: str) -> None:
        self.shop_id = shop_id


    def get_adapter(self, section: str, version: str) -> BaseAdapter:
        """Return adapter instance cached per (shop, section, version)."""
        return self.adapter_factory.get_adapter(self.shop_id, section, version)



