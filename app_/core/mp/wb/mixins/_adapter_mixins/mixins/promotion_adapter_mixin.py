"""Мета-миксин для подключения Promotion адаптера."""

from ..base_adapter_mixin import BaseAdapterMixin

# Flexible import for PromotionAdapterProtocol with a safe fallback
try:
    from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol
except Exception:
    class PromotionAdapterProtocol:  # type: ignore
        pass


class PromotionAdapterMixin(BaseAdapterMixin):
    @property
    def promotion_adapter(self) -> PromotionAdapterProtocol:
        """Получить адаптер для Promotion API."""
        return self._get_adapter("promotion")

# Public export for clarity in imports elsewhere
__all__ = ["PromotionAdapterMixin"]
