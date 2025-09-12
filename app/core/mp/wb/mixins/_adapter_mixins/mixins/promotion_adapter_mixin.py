"""Мета-миксин для подключения Promotion адаптера."""

from app.core.mp.wb.mixins._adapter_mixins.mixins.base_adapter_mixin import BaseAdapterMixin
from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol


class PromotionAdapterMixin(BaseAdapterMixin):
    @property
    def promotion_adapter(self) -> PromotionAdapterProtocol:
        """Получить адаптер для Promotion API."""
        return self._get_adapter("promotion")
