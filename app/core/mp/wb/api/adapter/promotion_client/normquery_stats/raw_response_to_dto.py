from typing import cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO, NormqueryStat
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import V0GetNormQueryStatsItem, \
    V0GetNormQueryStatsItemStat


def raw_response_to_dto(raw_stat: V0GetNormQueryStatsItem) -> NormqueryStatsDTO:

    stats: list[V0GetNormQueryStatsItemStat] = raw_stat.stats if raw_stat.stats else []
    result_stats: list[NormqueryStat] = []
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
        result_stat = NormqueryStat(
            norm_query=norm_query,
            ctr=ctr,
            cpm=cpm,
            add_to_cart=add_to_cart,
            orders=orders,
            cpc=cpc,
            avr_pos=avr_pos,
            views=views,
            clicks=clicks,
        )

        result_stats.append(result_stat)

    dto = NormqueryStatsDTO(
         adv_id=raw_stat.advert_id,
         nmid=raw_stat.nm_id,
         stats=result_stats,
     )

    return dto
