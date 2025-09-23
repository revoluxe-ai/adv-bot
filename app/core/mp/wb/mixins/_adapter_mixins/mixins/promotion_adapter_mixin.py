"""Мета-миксин для подключения Promotion адаптера."""


class PromotionAdapterMixin(BaseAdapterMixin):
    @property
    def promotion_adapter(self) -> "PromotionAdapterProtocol":
        """Получить адаптер для Promotion API."""
        return self._get_adapter("promotion")
