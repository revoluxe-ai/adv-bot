from .cabinet_adverts_list import CabinetAdvertsListAdapter
from .campaigns_management.adapter import CampaignsManagementAdapter
from .campaigns_info_v2.adapter import CampaignsInfoV2Adapter
from .fullstats import FullstatsAdapter
from .minus_phrases.adapter import MinusPhrasesAdapter
from .normquery_stats.adapter import NormqueryStatsAdapter
from .normquery_bids.adapter import NormqueryBidsAdapter
from .min_bids.adapter import MinBidsAdapter
from .finance.adapter import FinanceAdapter
from .common_bids.adapter import CommonBidsAdapter
from .product_cards.adapter import ProductCardsAdapter
from .promotion_count import PromotionCountAdapter


class PromotionClient:
    """Section-level адаптер, агрегирующий все адаптеры группы методов продвижения"""

    def __init__(
        self,
        minus_phrases_adapter: MinusPhrasesAdapter,
        normquery_stats_adapter: NormqueryStatsAdapter,
        normquery_bids_adapter: NormqueryBidsAdapter,
        min_bids_adapter: MinBidsAdapter,
        finance_adapter: FinanceAdapter,
        campaigns_management_adapter: CampaignsManagementAdapter,
        campaigns_info_v2_adapter: CampaignsInfoV2Adapter,
        cabinet_adverts_list_adapter: CabinetAdvertsListAdapter,
        promotion_count_adapter: PromotionCountAdapter,
        common_bids_adapter: CommonBidsAdapter,
        product_cards_adapter: ProductCardsAdapter,
        fullstats_adapter: FullstatsAdapter,
    ) -> None:
        self.__minus_phrases_adapter = minus_phrases_adapter
        self.__normquery_stats_adapter = normquery_stats_adapter
        self.__normquery_bids_adapter = normquery_bids_adapter
        self.__min_bids_adapter = min_bids_adapter
        self.__campaigns_management_adapter = campaigns_management_adapter
        self.__finance_adapter = finance_adapter
        self.__campaigns_info_v2_adapter = campaigns_info_v2_adapter
        self.__cabinet_adverts_list_adapter = cabinet_adverts_list_adapter
        self.__promotion_count_adapter = promotion_count_adapter
        self.__common_bids_adapter = common_bids_adapter
        self.__product_cards_adapter = product_cards_adapter
        self.__fullstats_adapter = fullstats_adapter

    @property
    def minus_phrases_adapter(self) -> MinusPhrasesAdapter:
        return self.__minus_phrases_adapter

    @property
    def normquery_stats_adapter(self) -> NormqueryStatsAdapter:
        return self.__normquery_stats_adapter

    @property
    def normquery_bids_adapter(self) -> NormqueryBidsAdapter:
        return self.__normquery_bids_adapter

    @property
    def min_bids_adapter(self) -> MinBidsAdapter:
        return self.__min_bids_adapter

    @property
    def finance_adapter(self) -> FinanceAdapter:
        return self.__finance_adapter

    @property
    def campaigns_info_v2_adapter(self) -> CampaignsInfoV2Adapter:
        return self.__campaigns_info_v2_adapter

    @property
    def cabinet_adverts_list_adapter(self) -> CabinetAdvertsListAdapter:
        return self.__cabinet_adverts_list_adapter

    @property
    def promotion_count_adapter(self) -> PromotionCountAdapter:
        return self.__promotion_count_adapter

    @property
    def campaigns_management_adapter(self) -> CampaignsManagementAdapter:
        return self.__campaigns_management_adapter

    @property
    def common_bids_adapter(self) -> CommonBidsAdapter:
        return self.__common_bids_adapter

    @property
    def product_cards_adapter(self) -> ProductCardsAdapter:
        return self.__product_cards_adapter

    @property
    def fullstats_adapter(self) -> FullstatsAdapter:
        return self.__fullstats_adapter
