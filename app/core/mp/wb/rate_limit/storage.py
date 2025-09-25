from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class RateLimitRecord:
    last_call_timestamp: float
    quota_used: int


class RateLimitStorage:
    """Centralized storage for rate limit state.

    Keyed by (shop_id, section, method).
    """

    def __init__(self) -> None:
        self._storage: Dict[Tuple[str, str, str], RateLimitRecord] = {}

    def get(self, shop_id: str, section: str, method: str) -> RateLimitRecord | None:
        return self._storage.get((shop_id, section, method))

    def set(self, shop_id: str, section: str, method: str, record: RateLimitRecord) -> None:
        self._storage[(shop_id, section, method)] = record

    def update(self, shop_id: str, section: str, method: str, **kwargs) -> None:
        """Partial update to a record."""
        raise NotImplementedError
