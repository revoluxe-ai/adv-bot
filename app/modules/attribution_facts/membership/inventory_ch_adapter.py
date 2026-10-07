"""CH read adapter nm_ids из shop_campaign_inventory."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from app.modules.attribution_facts.ports.shop_campaign_inventory import (
    ShopCampaignInventoryNmPort,
)

_SELECT_NM_IDS = """
SELECT
    argMax(nm_ids, version) AS nm_ids
FROM default_db.shop_campaign_inventory
WHERE shop_id = %(shop_id)s
  AND adv_id = %(adv_id)s
GROUP BY adv_id
""".strip()


class _QueryRows:
    def __init__(self, result_rows: Sequence[Sequence[object]]) -> None:
        self.result_rows = result_rows


class ShopCampaignInventoryNmClickHouse(Protocol):
    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows: ...


class ShopCampaignInventoryNmAdapter(ShopCampaignInventoryNmPort):
    """Read-only nm_ids fallback из inventory."""

    def __init__(self, client: ShopCampaignInventoryNmClickHouse) -> None:
        self._client = client

    async def nm_ids_for_adv(
        self,
        shop_id: str,
        physical_adv_id: int,
    ) -> tuple[int, ...] | None:
        rows = await self._client.query(
            _SELECT_NM_IDS,
            parameters={"shop_id": shop_id, "adv_id": physical_adv_id},
        )
        if not rows.result_rows:
            return None
        nm_ids_raw = rows.result_rows[0][0]
        if not isinstance(nm_ids_raw, (list, tuple)):
            return None
        result: list[int] = []
        for item in nm_ids_raw:
            if isinstance(item, bool):
                continue
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return tuple(result) if result else None
