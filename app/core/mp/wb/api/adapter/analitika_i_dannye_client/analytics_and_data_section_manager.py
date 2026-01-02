from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .poiskovye_zaprosy_po_vashim_tovaram import Adapter as PoiskovyeZaprosyAdapter
    from .voronka_prodazh import Adapter as VoronkaProdazhAdapter


class AnalyticAndDataClient:
    """Section-level адаптер, агрегирующий все адаптеры группы методов аналитики и данных"""

    def __init__(
        self,
        search_keywords_adapter: "PoiskovyeZaprosyAdapter",
        sales_funnel_adapter: "VoronkaProdazhAdapter",
    ) -> None:
        self.__search_keywords_adapter = search_keywords_adapter
        self.__sales_funnel_adapter = sales_funnel_adapter

    @property
    def search_keywords_adapter(self) -> "PoiskovyeZaprosyAdapter":
        """Адаптер для работы с поисковыми запросами по товарам"""
        return self.__search_keywords_adapter

    @property
    def sales_funnel_adapter(self) -> "VoronkaProdazhAdapter":
        """Адаптер для работы с воронкой продаж по товарам"""
        return self.__sales_funnel_adapter
