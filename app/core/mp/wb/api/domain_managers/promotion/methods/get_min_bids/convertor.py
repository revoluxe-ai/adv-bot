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

        auto_adv_id = adv.auto_adv_id
        items.append(
            GetMinBidsCommandItem(
                adv_id=auto_adv_id,
                nmids=nmids,
                placement_type=AdvPlacementType.AUTO_ADV,
            )
        )

        search_adv_id = adv.search_adv_id
        if search_adv_id is None:
            raise ValueError("Нет Поисковой кампании")
        items.append(
            GetMinBidsCommandItem(
                adv_id=search_adv_id,
                nmids=nmids,
                placement_type=AdvPlacementType.SEARCH_ADV,
            )
        )

    return GetMinBidsCommand(items=items)
