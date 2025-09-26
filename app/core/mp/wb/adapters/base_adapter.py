from __future__ import annotations

from threading import Lock
from typing import ClassVar

from app.core.mp.wb.rate_limit.storage import RateLimitStorage


class WBBaseAdapter:
    """Base class for WB adapters providing shared wiring and state."""

    section: ClassVar[str] = ""
    version: ClassVar[str] = ""

    _rate_limit_storage_cache: ClassVar[dict[tuple[str, str], RateLimitStorage]] = {}
    _rate_limit_storage_lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        shop_id: str,
    ) -> None:
        self.shop_id = shop_id
        self.section = type(self).section
        self.version = type(self).version
        self.rate_limit_storage = self._get_or_create_rate_limit_storage(shop_id, self.section)

    @classmethod
    def _get_or_create_rate_limit_storage(
        cls,
        shop_id: str,
        section: str,
    ) -> RateLimitStorage:
        key = (shop_id, section)
        with cls._rate_limit_storage_lock:
            storage = cls._rate_limit_storage_cache.get(key)
            if storage is None:
                storage = RateLimitStorage()
                cls._rate_limit_storage_cache[key] = storage
            return storage
