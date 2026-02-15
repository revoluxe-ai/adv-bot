from typing import Union, cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO, NormqueryStat
from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsItem,
    V0GetNormQueryStatsItemStat,
)
from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.types import (
    UNSET,
    Unset,
)


def _int_or_default(value: Union[int, float, Unset], default: int = 0) -> int:
    if isinstance(value, Unset):
        return default
    return int(value)


def _nullable_int(value: Union[int, float, Unset]) -> int | None:
    if isinstance(value, Unset):
        return None
    return int(value)


def _nullable_float(value: Union[int, float, Unset]) -> float | None:
    if isinstance(value, Unset):
        return None
    return float(value)


def raw_response_to_dto(raw_stat: V0GetNormQueryStatsItem) -> NormqueryStatsDTO:

    stats: list[V0GetNormQueryStatsItemStat] = raw_stat.stats if raw_stat.stats else []
    result_stats: list[NormqueryStat] = []
    for stat in stats:
        norm_query = cast(str, stat.norm_query) if stat.norm_query is not UNSET else ""
        ctr = _nullable_float(stat.ctr) or 0.0
        cpm = _nullable_float(stat.cpm)
        add_to_cart = _nullable_int(stat.atbs)
        orders = _int_or_default(stat.orders)
        cpc = _nullable_float(stat.cpc)
        views = _int_or_default(stat.views)
        clicks = _int_or_default(stat.clicks)
        avr_pos = _nullable_float(stat.avg_pos)
        spend = _nullable_float(stat.spend)
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
            spend=spend,
        )

        result_stats.append(result_stat)

    dto = NormqueryStatsDTO(
         adv_id=raw_stat.advert_id,
         nmid=raw_stat.nm_id,
         stats=result_stats,
     )

    return dto
