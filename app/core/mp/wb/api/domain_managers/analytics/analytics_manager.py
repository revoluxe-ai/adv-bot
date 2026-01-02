import typing

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

if typing.TYPE_CHECKING:
    import datetime

    from app.core.mp.wb.api.adapter.analitika_i_dannye_client import (
        AnalyticAndDataClient,
    )
    from app.core.mp.wb.dto import KeywordPosition
    from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
        CommonSaleStatRow,
    )


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

    async def get_sales_funnel_products_history(
        self,
        nmids: list[int],
        start: "datetime.date",
        end: "datetime.date",
    ) -> list["CommonSaleStatRow"]:
        # Локальный импорт, чтобы не раздувать импорт-граф доменных менеджеров
        from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.command import (
            SalesFunnelProductsHistoryCommand,
        )

        adapter = self.__wb_api_client.sales_funnel_adapter
        command = SalesFunnelProductsHistoryCommand(nmids=nmids, start=start, end=end)
        return await adapter.post_sales_funnel_products_history(command)
