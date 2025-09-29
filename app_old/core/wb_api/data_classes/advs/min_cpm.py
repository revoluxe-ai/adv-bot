__all__ = ("BidsData",)

from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field, field_validator


class PlacementType(str, Enum):
    """Типы размещения рекламы на Wildberries"""

    COMBINED = "combined"  # Комбинированный тип
    SEARCH = "search"  # Поиск
    RECOMMENDATION = "recommendation"  # Рекомендации


class Bid(BaseModel):
    """Ставка для конкретного типа размещения"""

    type: PlacementType
    value: int = Field(gt=0, description="Размер ставки в копейках")


class ProductBids(BaseModel):
    """Ставки для одного товара"""

    nmid: int = Field(alias="nm_id", description="ID товара на Wildberries")
    bids: List[Bid] = Field(description="Список ставок по типам размещения")

    @field_validator("bids")
    @classmethod
    def validate_bids_not_empty(cls, v) -> List[Bid]:
        if not v:
            raise ValueError("Список ставок не может быть пустым")
        return v

    @property
    def bids_dict(self) -> Dict[PlacementType, int]:
        """Словарь ставок для быстрого доступа: тип -> значение"""
        return {bid.type: bid.value for bid in self.bids}

    def get_bid(self, placement_type: PlacementType) -> Optional[int]:
        """Получить ставку для указанного типа размещения"""
        return self.bids_dict.get(placement_type)


class BidsData(BaseModel):
    """Данные о ставках для всех товаров"""

    bids: List[ProductBids] = Field(description="Список товаров со ставками")

    @field_validator("bids")
    @classmethod
    def validate_bids_not_empty(cls, v: List[ProductBids]) -> List[ProductBids]:
        if not v:
            raise ValueError("Список товаров не может быть пустым")
        return v

    @property
    def products_dict(self) -> Dict[int, ProductBids]:
        """Словарь товаров для быстрого доступа: nmid -> ProductBids"""
        return {product.nmid: product for product in self.bids}

    def get_min_bid(self, nmid: int, placement_type: PlacementType) -> Optional[int]:
        """
        Основной метод: получить ставку по ID товара и типу размещения

        Args:
            nmid: ID товара на Wildberries
            placement_type: Тип размещения рекламы

        Returns:
            Значение ставки в копейках или None если не найдено

        Example:
            >>> bids_data.get_bid(12345678, PlacementType.SEARCH)
            250
        """
        product = self.products_dict.get(nmid)
        if not product:
            return None
        return product.get_bid(placement_type)

    def get_all_bids_for_product(self, nmid: int) -> Optional[Dict[PlacementType, int]]:
        """Получить все ставки для товара в виде словаря"""
        product = self.products_dict.get(nmid)
        return product.bids_dict if product else None

    def has_product(self, nmid: int) -> bool:
        """Проверить есть ли товар в данных"""
        return nmid in self.products_dict

    def get_products_count(self) -> int:
        """Количество товаров в данных"""
        return len(self.bids)

    def get_nmids(self) -> List[int]:
        """Получить список всех nmid"""
        return list(self.products_dict.keys())
