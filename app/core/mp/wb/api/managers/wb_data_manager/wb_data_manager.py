from typing import List, Sequence
import datetime

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.dto import AdvMinNmidsBids, KeywordPosition
import logging
import typing

# TODO: Разобраться в NEO4j, почему так много выделяем и так мало грузит
# TODO: Внедрить контроль прогноза ключей, а то иногда не прогнозит



from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO
from typing import TYPE_CHECKING

from app.core.mp.wb.dto.adv_info import AdvInfoDTO, AdvInfoNmSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.shared.domains.wb.dto.current_common_bids_for_adv import CurrentCommonBidsForAdv

if TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.promotion_client.min_bids.command import (
        GetMinBidsCommand,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv

if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers import (
        AnalyticsManager,
        ProductsManager,
        PromotionManager,
        ReportsManager,
    )
    from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
        CommonSaleStatRow,
    )
    from app.core.mp.wb.api.generated.reports.v1.reports_client.models.orders_item import (
        OrdersItem,
    )
    from app.core.mp.wb.api.generated.reports.v1.reports_client.models.sales_item import (
        SalesItem,
    )

logger = logging.getLogger(__name__)


class NornQueryStat:
    pass


class WBDataManager:

    def __init__(
        self,
        analytics_manager: "AnalyticsManager",
        promotion_manager: "PromotionManager",
        products_manager: "ProductsManager",
        reports_manager: "ReportsManager",
    ):
        self._analytics_manager = analytics_manager
        self._promotion_manager = promotion_manager
        self._products_manager = products_manager
        self._reports_manager = reports_manager

    @property
    def promotion_manager(self) -> "PromotionManager":
        return self._promotion_manager

    @property
    def products_manager(self) -> "ProductsManager":
        return self._products_manager

    @property
    def reports_manager(self) -> "ReportsManager":
        """Менеджер statistics-api GET supplier orders/sales (INC-RO-06)."""
        return self._reports_manager

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list["OrdersItem"]:
        """Лента заказов поставщика (statistics-api); не funnel/fullstats."""
        return await self._reports_manager.get_supplier_orders(
            date_from=date_from,
            flag=flag,
        )

    async def get_supplier_sales(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> list["SalesItem"]:
        """Лента продаж поставщика (statistics-api)."""
        return await self._reports_manager.get_supplier_sales(
            date_from=date_from,
            flag=flag,
        )

    async def get_keywords_positions_from_wb_api(
        self,
        nmid: int,
        keywords: Sequence[CalculatedKeyword],
        for_last_days: int,
    ) -> Sequence[KeywordPosition]:

        positions: Sequence[KeywordPosition] = (
            await self._analytics_manager.get_keywords_positions(
                nmid, keywords, for_last_days
            )
        )

        return positions

    async def get_sales_funnel_products_history(
        self,
        nmids: list[int],
        start: datetime.date,
        end: datetime.date,
    ) -> list["CommonSaleStatRow"]:
        return await self._analytics_manager.get_sales_funnel_products_history(
            nmids=nmids,
            start=start,
            end=end,
        )


    async def get_norn_query_stat_for_date_range(
        self,
        complex_advs: list["ComplexAdv"],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> List[NormqueryStatsDTO] | None:
        """Получить статистику normquery за указанный диапазон дат."""

        return await self._promotion_manager.get_normquery_stats(
            complex_advs,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_current_bids_for_advs(
        self,
        complex_advs: list["ComplexAdv"],
    ) -> list[NormqueryBidDTO] | None:
        """Получить текущие ставки по поисковым кластерам для рекламных кампаний."""

        return await self._promotion_manager.get_normquery_bids(
            complex_advs,
        )

    async def get_min_bids(self, advs: list["ComplexAdv"]) -> AdvMinNmidsBids | None:
        """Получить минимальные ставки CPM (auto + search) для списка РК."""

        return await self._promotion_manager.get_min_bids_for_complex_adv(advs)

    async def get_min_bids_for_command(
        self, command: "GetMinBidsCommand"
    ) -> AdvMinNmidsBids | None:
        """Минимальные ставки по готовой команде (частичный набор nmids на item)."""

        return await self._promotion_manager.get_min_bids_for_command(command)

    async def get_min_bids_per_command_item(
        self, command: "GetMinBidsCommand"
    ) -> list[AdvMinNmidsBids] | None:
        """По одному результату на command item (для записи min_bids v2 в Redis по adv_id)."""

        return await self._promotion_manager.get_min_bids_per_command_item(command)

    async def get_full_adv_stat(
        self,
        adv_ids: list[int],
        dates: list[datetime.date],
    ) -> list[FullAdvStat]:
        """Полная статистика кампаний за указанные даты (v3 fullstats)."""
        return await self._promotion_manager.get_full_adv_stat(adv_ids, dates)

    async def get_advs_info(
        self, advs: list["ComplexAdv"], *, get_auto: bool = True
    ) -> dict[int, "AdvInfoDTO"]:
        return await self._promotion_manager.get_campaigns_info(advs, get_auto=get_auto)


    async def get_current_common_bids_for_search_adv(self,
                                                     advs: list["ComplexAdv"])  \
                                                        -> dict[int, CurrentCommonBidsForAdv | None]:
        adv_infos: dict[int, AdvInfoDTO] = await self.get_advs_info(advs, get_auto=False)
        result: dict[int, CurrentCommonBidsForAdv | None] = {}
        for adv in advs:
            complex_adv_id = adv.adv_id
            adv_info = adv_infos.get(complex_adv_id)
            if adv_info is None:
                continue
            nmids_settings: list[AdvInfoNmSetting] = adv_info.search_adv.nmids_settings

            nmid_to_current_bid: dict[int, int] = {}
            for nmid_setting in nmids_settings:
                nmid = nmid_setting.nmid
                current_bid = nmid_setting.search_bid_kopecks
                nmid_to_current_bid[nmid] = current_bid

            current_adv_bid = CurrentCommonBidsForAdv(
                adv_id_of_wb_adv=adv_info.search_adv.adv_id,
                nmids_to_bids=nmid_to_current_bid,
            )
            result[adv.adv_id] = current_adv_bid
        return result







