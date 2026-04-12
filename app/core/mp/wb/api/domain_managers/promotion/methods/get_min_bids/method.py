from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.min_bids import (
    MinBidsAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.min_bids.dto import MinBidForNmid
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from . import convertor


def _aggregate_min_bid_results(results: list[MinBidForNmid]) -> AdvMinNmidsBids:
    auto: dict[int, int] = {}
    search: dict[int, int] = {}

    for bid in results:
        rounded_cpm = (bid.min_cpm + 99) // 100
        if bid.placement_type == AdvPlacementType.AUTO_ADV:
            auto[bid.nmid] = rounded_cpm
        elif bid.placement_type == AdvPlacementType.SEARCH_ADV:
            search[bid.nmid] = rounded_cpm

    return AdvMinNmidsBids(auto=auto, search=search)


async def get_min_bids_for_command(
    min_bids_adapter: MinBidsAdapter,
    command: GetMinBidsCommand,
) -> AdvMinNmidsBids | None:
    if not command.items:
        return None

    results = await min_bids_adapter.post_api_advert_v1_bids_min(command)
    return _aggregate_min_bid_results(results)


async def get_min_bids(
    min_bids_adapter: MinBidsAdapter,
    complex_advs: list[ComplexAdv],
) -> AdvMinNmidsBids | None:
    if not complex_advs:
        return None

    command = convertor.dto_to_command(complex_advs)
    return await get_min_bids_for_command(min_bids_adapter, command)
















