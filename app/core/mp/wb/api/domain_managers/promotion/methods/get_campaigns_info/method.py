from __future__ import annotations

from typing import Sequence

from app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.adapter import (
    CampaignsInfoV2Adapter,
)
from app.core.mp.wb.api.adapter.promotion_client.campaigns_info_v2.raw_response_to_dto import (
    convert as convert_to_simple,
)
from app.core.mp.wb.dto.adv_info import AdvInfoDTO, AdvInfoSimple
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


async def get_campaigns_info(
    campaigns_info_adapter: CampaignsInfoV2Adapter,
    complex_advs: Sequence[ComplexAdv],
    *,
    get_auto: bool = True,
) -> dict[int, AdvInfoDTO]:

    all_ids: set[int] = set()
    for complex_adv in complex_advs:
        if get_auto:
            all_ids.add(complex_adv.auto_adv_id)
        if search_adv_id := complex_adv.search_adv_id:
            all_ids.add(int(search_adv_id))

    campaigns = await campaigns_info_adapter.get_campaigns_info(list(all_ids))
    adv_info_map: dict[int, AdvInfoSimple] = {campaign.id: convert_to_simple(campaign) for campaign in campaigns}

    result: dict[int, AdvInfoDTO] = {}
    for complex_adv in complex_advs:
        if complex_adv.search_adv is None:
            raise ValueError("Search campaign is required to build AdvInfoDTO")
        if not (search_adv_id := complex_adv.search_adv_id):
            raise ValueError("Search campaign is required to build AdvInfoDTO")
        search_info : AdvInfoSimple = adv_info_map[search_adv_id]
        dto: AdvInfoDTO = AdvInfoDTO(
            adv_id=complex_adv.adv_id,
            auto_adv=adv_info_map.get(complex_adv.auto_adv_id)
            if get_auto
            else None,
            search_adv=search_info,
        )
        result[complex_adv.adv_id] = dto

    return result
