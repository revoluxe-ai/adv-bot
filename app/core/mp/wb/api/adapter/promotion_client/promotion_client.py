from .minus_phrases.adapter import MinusPhrasesAdapter
from .normquery_stats.adapter import NormqueryStatsAdapter


class PromotionClient:
    """Section-level адаптер, агрегирующий все адаптеры группы методов продвижения"""

    def __init__(
        self,
        minus_phrases_adapter: MinusPhrasesAdapter,
        normquery_stats_adapter: NormqueryStatsAdapter,
    ) -> None:
        self.__minus_phrases_adapter = minus_phrases_adapter
        self.__normquery_stats_adapter = normquery_stats_adapter

    @property
    def minus_phrases_adapter(self) -> MinusPhrasesAdapter:
        return self.__minus_phrases_adapter

    @property
    def normquery_stats_adapter(self) -> NormqueryStatsAdapter:
        return self.__normquery_stats_adapter
