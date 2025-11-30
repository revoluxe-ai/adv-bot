from typing import Sequence

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCard, WBCategory
from .row_stat_dto import RowStatDTO
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO
from app.utils.db.session_maker import get_async_session_maker as sm

async def norn_query_dto_to_raw_stat_dto(norm_query_stat_dtos: Sequence["NormqueryStatsDTO"]) -> list[RowStatDTO]:
    all_nmids = {stat.nmid for stat in norm_query_stat_dtos}

    stmt = select(WBCard.nmid, WBCategory.wb_category_name)\
       .join(WBCard.wb_category)\
            .where(WBCard.nmid.in_(all_nmids))

    async with sm(read_only=True) as session:
        category_rows = await session.execute(stmt)
    nmid_to_category = {row[0]: row[1] for row in category_rows}
    rows_dto = []
    for stat_dto in norm_query_stat_dtos:
        adv_id = stat_dto.adv_id
        nmid = stat_dto.nmid
        stat_date = stat_dto.day
        for st in stat_dto.stats:
            row_dto = RowStatDTO(
                adv_id=adv_id,
                nmid=nmid,
                norm_query=st.norm_query,
                cpm=st.cpm,
                ctr=st.ctr,
                clicks=st.clicks,
                views=st.views,
                avr_pos=st.avr_pos,
                add_to_cart=st.add_to_cart,
                orders=st.orders,
                cpc=st.cpc,
                wb_category=nmid_to_category[nmid],
                date=stat_date,
            )
            rows_dto.append(row_dto)
    return rows_dto