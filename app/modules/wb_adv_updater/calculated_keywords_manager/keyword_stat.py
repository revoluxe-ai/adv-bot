from datetime import datetime

from pydantic import BaseModel, Field


class KeywordStat(BaseModel):
    text: str = Field(alias="norm_query")
    position: float = Field(alias="position")
    timestamp: datetime = Field(alias="timestamp")
    views: int = Field(alias="views")
    clicks: int = Field(alias="clicks")
    add_to_cart: int = Field(alias="add_to_cart")
    orders: int = Field(alias="orders")
    spend: float = Field(alias="spend")
    cpc: float = Field(alias="cpc")
    cpm: float = Field(alias="cpm")
    base_cart_to_order_conv: float = Field(alias="base_cart_to_order_conv")
    expected_orders_from_cart: float = Field(alias="expected_orders_from_cart")
    expected_orders: float = Field(alias="expected_orders")
    final_rating: float = Field(alias="final_rating")
    total_views: int = Field(alias="views_all_time")
    total_orders: int = Field(alias="orders_all_time")

    model_config = {
        "populate_by_name": True, # позволяет загружать данные как по имени, так и по алиасу
    }

    @property
    def ctr(self) -> float:
        if self.views > 0:
            return self.clicks / self.views
        else:
            return 0.0