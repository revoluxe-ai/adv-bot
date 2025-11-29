from typing import cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import V0GetNormQueryStatsItem

def raw_response_to_dto(item: V0GetNormQueryStatsItem, adv_id: int, nmid: int) -> list[NormqueryStatsDTO] | None:
    if not item.stats:
        return None
    stats = item.stats
    dtos: list[NormqueryStatsDTO] = []
    for stat in stats:
        norm_query = cast(str, stat.norm_query)
        ctr = cast(float, stat.ctr)
        cpc = cast(int, stat.cpc)
        add_to_cart = cast(int, stat.atbs)
        orders = cast(int, stat.orders)
        cpm = cast(int, stat.cpm)
        views = cast(int, stat.views)
        clicks = cast(int, stat.clicks)
        avr_pos = cast(float, stat.avg_pos)
        add_keys = stat.additional_keys
        add_properties = stat.additional_properties
        dto = NormqueryStatsDTO(
            adv_id=adv_id,
            nmid=nmid,
            norm_query=norm_query,
            ctr=ctr,
            cpm=cpm,
            add_to_cart=add_to_cart,
            orders=orders,
            add_properties=add_properties,
            cpc=cpc,
            avr_pos=avr_pos,
            add_keys=add_keys,
            views=views,
            clicks=clicks,
        )
        dtos.append(dto)

    return dtos
