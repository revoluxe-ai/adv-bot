from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
    GetMinBidsCommand,
    GetMinBidsCommandItem,
)
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


def dto_to_command(complex_advs: list[ComplexAdv]) -> GetMinBidsCommand:
    items: list[GetMinBidsCommandItem] = []

    for adv in complex_advs:
        nmids = adv.nmids
        if not nmids:
            continue

        items.append(
            GetMinBidsCommandItem(
                adv_id=adv.auto_adv_id,
                nmids=nmids,
                placement_type=AdvPlacementType.AUTO_ADV,
            )
        )

        if search_adv := adv.search_adv:
            items.append(
                GetMinBidsCommandItem(
                    adv_id=search_adv.adv_id,
                    nmids=nmids,
                    placement_type=AdvPlacementType.SEARCH_ADV,
                )
            )

    return GetMinBidsCommand(items=items)

