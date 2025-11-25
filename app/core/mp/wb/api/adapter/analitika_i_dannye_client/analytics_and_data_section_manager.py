from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .poiskovye_zaprosy_po_vashim_tovaram import Adapter as PoiskovyeZaprosyAdapter


class AnalyticAndDataClient:
    """Section-level адаптер, агрегирующий все адаптеры группы методов аналитики и данных"""

    def __init__(self, search_keywords_adapter: "PoiskovyeZaprosyAdapter") -> None:
        self.__search_keywords_adapter = search_keywords_adapter

    @property
    def search_keywords_adapter(self) -> "PoiskovyeZaprosyAdapter":
        """Адаптер для работы с поисковыми запросами по товарам"""
        return self.__search_keywords_adapter
