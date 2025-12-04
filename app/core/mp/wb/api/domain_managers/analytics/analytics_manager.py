import typing

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.analitika_i_dannye_client import (
        AnalyticAndDataClient,
    )
    from app.core.mp.wb.dto import KeywordPosition


class AnalyticsManager:

    def __init__(self, wb_api_client: "AnalyticAndDataClient") -> None:
        self.__wb_api_client = wb_api_client

    async def get_keywords_positions(
        self,
        nmid: int,
        keywords: typing.Sequence[CalculatedKeyword],
        for_last_days: int = 7,
    ) -> typing.Sequence["KeywordPosition"]:
        from .methods.get_keyword_positions import request

        texts: list[str] = [kw.text for kw in keywords]
        get_keyword_positions_method = (
            self.__wb_api_client.search_keywords_adapter.post_api_v2_search_report_product_orders
        )
        return await request(get_keyword_positions_method, nmid, texts, for_last_days)
