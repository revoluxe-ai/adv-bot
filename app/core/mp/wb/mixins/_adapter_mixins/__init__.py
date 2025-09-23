"""Мета-миксины для подключения адаптеров."""

from .base_adapter_mixin import BaseAdapterMixin
from .media_adapter_mixin import MediaAdapterMixin
from .promotion_adapter_mixin import PromotionAdapterMixin

__all__ = [
    "BaseAdapterMixin",
    "PromotionAdapterMixin",
    "MediaAdapterMixin",
]
