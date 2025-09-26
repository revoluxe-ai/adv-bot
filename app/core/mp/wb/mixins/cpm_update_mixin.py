from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence, TYPE_CHECKING, cast

from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import (
    PromotionAdapterProtocol,
)
from app.shared.application.commands.search_adv_bid_update import UpdateBidsForShopCommand


if TYPE_CHECKING:
    from app.core.mp.wb.base_wb_api import BaseWBApi


class CPMUpdateMixin:
    """Mixin that routes CPM update commands through the promotion adapter."""

    promotion_adapter_version: int = 1

    def _promotion_adapter(self: "BaseWBApi"):
        adapter = self.get_adapter("promotion", self.promotion_adapter_version)
        return cast(PromotionAdapterProtocol, adapter)

    @staticmethod
    def _to_command(adv_id: int, nm_bids: Sequence[Mapping[str, int]]) -> UpdateBidsForShopCommand:
        normalized: list[dict[str, int]] = []
        for row in nm_bids:
            if "nm" in row and "cpm" in row:
                normalized.append({"nm": int(row["nm"]), "cpm": int(row["cpm"])})
                continue
            nm: Optional[int] = None
            if "nmid" in row:
                nm = int(row["nmid"])
            elif "nmId" in row:
                nm = int(row["nmId"])
            if nm is None:
                raise ValueError(f"Cannot determine nm from payload row: {row!r}")
            if "cpm" in row:
                cpm = int(row["cpm"])
            elif "bid" in row:
                cpm = int(row["bid"])
            else:
                raise ValueError(f"Cannot determine CPM/bid from payload row: {row!r}")
            normalized.append({"nm": nm, "cpm": cpm})
        return UpdateBidsForShopCommand(adv_id=adv_id, bids=normalized)

    async def update_bids_for_shop(
        self: "BaseWBApi",
        *,
        adv_id: int,
        nm_bids: Sequence[Mapping[str, int]] | Iterable[Mapping[str, int]],
    ) -> None:
        """Normalize incoming bids and delegate to promotion adapter."""
        command = self._to_command(adv_id, list(nm_bids))
        adapter = self._promotion_adapter()
        await adapter.update_bids(
            adv_id=command.adv_id,
            nm_bids=[bid.as_dict() for bid in command.normalized_bids],
        )
