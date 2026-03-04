"""Tests for phrases_processor white-list helpers."""

import pytest

from app.modules.wb_adv_updater import phrases_processor
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from tests.factories.keyword_pipeline import (
    CalculatedKeywordFactory,
    HardStatus,
)

# CPM=1000 → orders_per_1000_rub = conv_views_to_orders * 1_000_000 / 1000
_CPM_FOR_ORDERS_TEST = 1000.0


@pytest.mark.unit
class TestGetMinOrdersPer1000Rub:
    """get_min_orders_per_1000_rub возвращает минимум заказов на 1000₽ среди ключей в белом списке."""

    def test_returns_min_among_white_list(self) -> None:
        """Минимум среди ключей в белом списке (conv=0.01→10, conv=0.05→50 при CPM=1000)."""
        cpm_sources = KeywordCpmSources(cpm_set_bid=int(_CPM_FOR_ORDERS_TEST))
        kw_low = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.01,
            cluster_stat__cpm=_CPM_FOR_ORDERS_TEST,
            cpm_sources=cpm_sources,
        )
        kw_high = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.05,
            cluster_stat__cpm=_CPM_FOR_ORDERS_TEST,
            cpm_sources=cpm_sources,
        )
        result = phrases_processor.get_min_orders_per_1000_rub([kw_low, kw_high])
        assert result == 10.0  # 0.01 * 1e6 / 1000

    def test_returns_none_for_empty_white_list(self) -> None:
        """Нет ключей в белом списке — None."""
        kw = CalculatedKeywordFactory.build(keyword_setting__hard_status=HardStatus.BLACKLIST)
        result = phrases_processor.get_min_orders_per_1000_rub([kw])
        assert result is None

    def test_ignores_non_white_list(self) -> None:
        """Учитываются только hard_status == 2 (белый список)."""
        cpm_sources = KeywordCpmSources(cpm_set_bid=int(_CPM_FOR_ORDERS_TEST))
        kw_white = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.005,  # 5.0 заказов на 1000₽
            cluster_stat__cpm=_CPM_FOR_ORDERS_TEST,
            cpm_sources=cpm_sources,
        )
        kw_black = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.BLACKLIST,
            cluster_stat__conv_views_to_orders=0.001,  # 1.0 — должен игнорироваться
            cluster_stat__cpm=_CPM_FOR_ORDERS_TEST,
            cpm_sources=cpm_sources,
        )
        result = phrases_processor.get_min_orders_per_1000_rub([kw_white, kw_black])
        assert result == 5.0


@pytest.mark.unit
class TestGetMinConvViewsToOrders:
    """get_min_conv_views_to_orders возвращает минимум конверсии показы→заказы среди ключей в белом списке."""

    def test_returns_min_among_white_list(self) -> None:
        """Минимум конверсии среди ключей в белом списке."""
        kw_low = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.01,
        )
        kw_high = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.05,
        )
        result = phrases_processor.get_min_conv_views_to_orders([kw_low, kw_high])
        assert result == 0.01

    def test_returns_none_for_empty_white_list(self) -> None:
        """Нет ключей в белом списке — None."""
        kw = CalculatedKeywordFactory.build(keyword_setting__hard_status=HardStatus.BLACKLIST)
        result = phrases_processor.get_min_conv_views_to_orders([kw])
        assert result is None

    def test_ignores_non_white_list(self) -> None:
        """Учитываются только hard_status == 2 (белый список)."""
        kw_white = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.WHITELIST,
            cluster_stat__conv_views_to_orders=0.02,
        )
        kw_black = CalculatedKeywordFactory.build(
            keyword_setting__hard_status=HardStatus.BLACKLIST,
            cluster_stat__conv_views_to_orders=0.10,
        )
        result = phrases_processor.get_min_conv_views_to_orders([kw_white, kw_black])
        assert result == 0.02
