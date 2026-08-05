"""Секция Statistics (statistics-api) для Reports adapter."""

from app.core.mp.wb.api.adapter.abc_group_client import AbcAdapter
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum


class BaseStatisticsSectionAdapter(AbcAdapter):
    """Базовый адаптер секции STATISTICS (host statistics-api.wildberries.ru)."""

    section = SectionsEnum.STATISTICS
