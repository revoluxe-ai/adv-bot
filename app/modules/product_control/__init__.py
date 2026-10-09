"""
Домен product control: DRR-профили, enrollment, чистые резолверы и порты цены.

Связь с WB Sky: каноническая идентичность управления ``(shop_id, nmid)``;
кампании остаются execution-слоем до Slice D adapter.
"""

from app.modules.product_control.domain.effective_control_resolver import (
    EffectiveControlResolver,
)
from app.modules.product_control.domain.product_cpo_resolver import ProductCpoResolver

__all__ = [
    "EffectiveControlResolver",
    "ProductCpoResolver",
]
