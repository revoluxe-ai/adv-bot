from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.mp.wb.api.adapter.promotion_client.min_bids import (
    MinBidsAdapter,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType

from . import convertor

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )


async def get_min_bids(
    min_bids_adapter: MinBidsAdapter,
    complex_advs: list["ComplexAdv"],
) -> AdvMinNmidsBids | None:
    if not complex_advs:
        return None

    command = convertor.dto_to_command(complex_advs)
    if not command.items:
        return None

    results = await min_bids_adapter.post_api_advert_v1_bids_min(command)
    auto: dict[int, int] = {}
    search: dict[int, int] = {}

    for bid in results:
        if bid.placement_type == AdvPlacementType.AUTO_ADV:
            auto[bid.nmid] = int(bid.min_cpm/100)
        elif bid.placement_type == AdvPlacementType.SEARCH_ADV:
            search[bid.nmid] = int(bid.min_cpm/100)

    return AdvMinNmidsBids(auto=auto, search=search)
















