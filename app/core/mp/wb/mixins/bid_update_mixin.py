from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Sequence, cast

if TYPE_CHECKING:
    from app.core.mp.wb.base_wb_api import BaseWBApi
    from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol

from app.shared.application.commands.search_adv_bid_update import UpdateBidsForShopCommand

class BidUpdateMixin:

    @staticmethod
    def _to_command(adv_id: int, nm_bids: Sequence[Mapping[str, int]]) -> UpdateBidsForShopCommand:
        normalized: list[dict[str, int]] = []
        for row in nm_bids:
            if "nm" in row and "cpm" in row:
                normalized.append({"nm": int(row["nm"]), "cpm": int(row["cpm"])})
                continue
            nm = row.get("nm") or row.get("nmid") or row.get("nmId")
            if nm is None:
                raise ValueError(f"Cannot determine nm from payload row: {row!r}")
            bid_val = row.get("cpm") or row.get("bid")
            if bid_val is None:
                raise ValueError(f"Cannot determine bid/cpm from payload row: {row!r}")
            normalized.append({"nm": int(nm), "cpm": int(bid_val)})
        return UpdateBidsForShopCommand(adv_id=adv_id, bids=normalized)

    async def update_bids(
        self: BaseWBApi,
        *,
        adv_id: int,
        nm_bids: Sequence[Mapping[str, int]] | Mapping[str, int],
    ) -> None:
        """Delegate to promotion adapter to update bids."""
        payload = nm_bids
        if isinstance(nm_bids, Mapping):
            payload_list: list[Mapping[str, int]] = [nm_bids]
        else:
            payload_list = list(nm_bids)
        command = self._to_command(adv_id, payload_list)
        promotion_adapter = self.get_adapter(section="promotion", version=1)
        typed_adapter = cast(PromotionAdapterProtocol, promotion_adapter)
        await typed_adapter.update_bids(
            adv_id=command.adv_id,
            nm_bids=[bid.as_dict() for bid in command.normalized_bids],
        )


