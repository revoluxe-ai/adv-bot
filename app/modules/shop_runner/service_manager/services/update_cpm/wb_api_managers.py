from __future__ import annotations

"""WB API facades for promotion section built on shared mixins."""

from typing import Iterable, Mapping, Optional, Sequence

from app.core.mp.wb.base_wb_api import BaseWBApi
from app.core.mp.wb.mixins.cpm_update_mixin import CPMUpdateMixin
from app.core.mp.wb.mixins.current_bid_mixin import CurrentBidMixin
from app.core.mp.wb.mixins.min_bid_mixin import MinBidMixin


class WBApiDataGetter(MinBidMixin, CurrentBidMixin, BaseWBApi):
    """Expose read-only promotion helpers scoped to a single shop."""

    def __init__(self, shop_id: str) -> None:
        super().__init__(shop_id)

    async def get_min_bid_for_nmids(
        self,
        shop_id: Optional[str] = None,
        *,
        adv_id: int,
        nmids: Sequence[int] | Iterable[int],
    ) -> dict[int, int]:
        if shop_id is not None and shop_id != self.shop_id:
            raise ValueError("WBApiDataGetter scoped to different shop_id")
        return await MinBidMixin.get_min_bids(self, adv_id, list(nmids))

    async def get_current_bids(
        self,
        shop_id: Optional[str] = None,
        *,
        adv_id: int,
        nmids: Sequence[int] | Iterable[int],
    ) -> dict[int, int]:
        if shop_id is not None and shop_id != self.shop_id:
            raise ValueError("WBApiDataGetter scoped to different shop_id")
        return await CurrentBidMixin.get_current_bids(self, adv_id, list(nmids))


class WBApiCpmUpdater(CPMUpdateMixin, BaseWBApi):
    """Expose write operations for promotion CPM updates."""

    def __init__(self, shop_id: str) -> None:
        super().__init__(shop_id)

    async def update_bids_for_shop(
        self,
        *,
        adv_id: int,
        nm_bids: Sequence[Mapping[str, int]] | Iterable[Mapping[str, int]],
    ) -> None:
        await CPMUpdateMixin.update_bids_for_shop(self, adv_id=adv_id, nm_bids=list(nm_bids))

    async def update_bids(
        self,
        shop_id: Optional[str] = None,
        *,
        adv_id: int,
        nm_bids: Sequence[Mapping[str, int]] | Iterable[Mapping[str, int]],
    ) -> None:
        if shop_id is not None and shop_id != self.shop_id:
            raise ValueError("WBApiCpmUpdater scoped to different shop_id")
        await self.update_bids_for_shop(adv_id=adv_id, nm_bids=nm_bids)

