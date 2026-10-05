"""Port: authoritative WB promotion v2 read (raw JSON boundary)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class WbPromotionV2ReadPort(Protocol):
    """Read-only WB promotion v2 transport."""

    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, object]]:
        """Fetch raw advert dicts before generated-client default injection."""
        ...
