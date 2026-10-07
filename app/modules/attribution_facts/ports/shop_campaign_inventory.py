"""Порт чтения nm_ids из shop_campaign_inventory (bounded fallback)."""

from __future__ import annotations

from typing import Protocol


class ShopCampaignInventoryNmPort(Protocol):
    """Read-only nm_ids по physical adv_id."""

    async def nm_ids_for_adv(
        self,
        shop_id: str,
        physical_adv_id: int,
    ) -> tuple[int, ...] | None:
        """
        Вернуть nm_ids из inventory или None если строка отсутствует.

        Args:
            shop_id: Идентификатор магазина.
            physical_adv_id: WB advertId.
        """
        ...
