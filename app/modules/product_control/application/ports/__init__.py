"""Transport-independent read ports для product control."""

from app.modules.product_control.application.ports.pricing import ProductPricingReader
from app.modules.product_control.application.ports.sales_economics import (
    ProductSalesEconomicsReader,
)

__all__ = [
    "ProductPricingReader",
    "ProductSalesEconomicsReader",
]
