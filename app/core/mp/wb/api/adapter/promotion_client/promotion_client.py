from .minus_phrases.adapter import MinusPhrasesAdapter
from .normquery_stats.adapter import NormqueryStatsAdapter
from .normquery_bids.adapter import NormqueryBidsAdapter
from .min_bids.adapter import MinBidsAdapter
from .finance.adapter import FinanceAdapter


class PromotionClient:
    """Section-level адаптер, агрегирующий все адаптеры группы методов продвижения"""

    def __init__(
        self,
        minus_phrases_adapter: MinusPhrasesAdapter,
        normquery_stats_adapter: NormqueryStatsAdapter,
        normquery_bids_adapter: NormqueryBidsAdapter,
        min_bids_adapter: MinBidsAdapter,
        finance_adapter: FinanceAdapter,
    ) -> None:
        self.__minus_phrases_adapter = minus_phrases_adapter
        self.__normquery_stats_adapter = normquery_stats_adapter
        self.__normquery_bids_adapter = normquery_bids_adapter
        self.__min_bids_adapter = min_bids_adapter
        self.__finance_adapter = finance_adapter

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
