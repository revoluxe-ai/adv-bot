"""Keyword calculation package.

Avoid importing ``CalculatedKeywordsManager`` at package import time: it pulls in
shop_runner → plan_fact → common_advs_stat while that stack may still be loading
(calculated_keywords_manager.dto is imported from common_advs_stat.data_manager).
Use lazy export via :func:`__getattr__` at runtime; ``TYPE_CHECKING`` import
satisfies static analysis and ``__all__`` without eager loading in production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["CalculatedKeywordsManager"]

if TYPE_CHECKING:
    from .calculated_keywords_manager import CalculatedKeywordsManager


def __getattr__(name: str):
    if name == "CalculatedKeywordsManager":
        from .calculated_keywords_manager import CalculatedKeywordsManager

        return CalculatedKeywordsManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
