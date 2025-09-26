from __future__ import annotations

from app.core.mp.wb.rate_limit.storage import RateLimitStorage


class BaseAdapter:
    def __init__(self, shop_id: str, rate_limit_storage: RateLimitStorage) -> None:
        self.shop_id = shop_id
        self.rate_limit_storage = rate_limit_storage
        # These will be set by concrete adapters
        self.section: str = ""
        self.version: int = 0
